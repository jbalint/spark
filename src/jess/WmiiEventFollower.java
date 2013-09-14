import java.util.*;
import java.sql.*;
import java.io.*;
import java.net.Socket;
import java.util.logging.Logger;
import java.util.logging.Level;

public class WmiiEventFollower {

	private static final Logger log = Logger.getLogger(WmiiEventFollower.class.getName());

	// db
	Connection c;
	int sessionId;
	PreparedStatement insertEventStatement;
	PreparedStatement insertClientStatement;
	Map<String, Integer> clientDbIds = new HashMap<>();

	// spark
	Socket sparkSocket;
	BufferedWriter sparkWriter;

	// cache
	Map<String, ClientInfo> clientInfo = new HashMap<>();

	static class ClientInfo {
		String xclass;
		String program;
		String label;
	}

	public WmiiEventFollower() throws SQLException {
	}

	private void sparkInit() throws IOException {
		sparkSocket = new Socket("localhost", 9002);
		sparkWriter = new BufferedWriter(new OutputStreamWriter(sparkSocket.getOutputStream()));
	}

	private void sendEventToSpark(String event[]) throws IOException {
		// event[1] may be literally `<nil>' if we go to a tag/view with no clients
		if ("ClientFocus".equals(event[0]) && !"<nil>".equals(event[1])) {
			sparkWriter.write(String.format("addfact (WmiiHasFocus \"%s\")\n", event[1]));
			sparkWriter.flush();
		}
	}

	private void databaseInit() throws SQLException {
		c = DriverManager.getConnection("jdbc:mysql://localhost/events", "events", "temp4now");

		// init new wmii event follower session
		Statement s = c.createStatement();
		s.executeUpdate("insert into wmii_session (start_time) values (now())",
						Statement.RETURN_GENERATED_KEYS);
		ResultSet rs = s.getGeneratedKeys();
		rs.next();
		sessionId = rs.getInt(1);
		rs.close();

		insertEventStatement = c.prepareStatement("insert into wmii_focus_event (session_id, client_id, focus_time) " +
												  " values (?, ?, now(6))");
		insertClientStatement = c.prepareStatement("insert into wmii_client (session_id, id, xclass, program, label) " +
												   "values (?, ?, ?, ?, ?)",
												   Statement.RETURN_GENERATED_KEYS);
	}

	private int getClientDbId(String idString) throws SQLException, IOException {
		Integer id = clientDbIds.get(idString);
		// existing
		if (id != null)
			return id;
		// new
		ClientInfo ci = getClientInfo(idString);
		insertClientStatement.setInt(1, sessionId);
		insertClientStatement.setString(2, idString);
		insertClientStatement.setString(3, ci.xclass);
		insertClientStatement.setString(4, ci.program);
		insertClientStatement.setString(5, ci.label);
		insertClientStatement.executeUpdate();
		ResultSet rs = insertClientStatement.getGeneratedKeys();
		rs.next();
		id = rs.getInt(1);
		rs.close();
		clientDbIds.put(idString, id);
		return id;
	}

	private void writeEventToDb(String event[]) throws SQLException, IOException {
		if ("ClientFocus".equals(event[0]) && !"<nil>".equals(event[1])) {
			insertEventStatement.setInt(1, sessionId);
			insertEventStatement.setInt(2, getClientDbId(event[1]));
			insertEventStatement.executeUpdate();
		}
	}

	private ClientInfo getClientInfo(String idString) throws IOException {
		ClientInfo ci = clientInfo.get(idString);
		if (ci != null)
			return ci;
		ci = new ClientInfo();

		String labelPath = String.format("/client/%s/label", idString);
		Process readerProcess = new ProcessBuilder("wmiir", "read", labelPath).start();
		BufferedReader br = new BufferedReader(new InputStreamReader(readerProcess.getInputStream()));
		ci.label = br.readLine();
		readerProcess.destroy();

		String propsPath = String.format("/client/%s/props", idString);
		readerProcess = new ProcessBuilder("wmiir", "read", propsPath).start();
		br = new BufferedReader(new InputStreamReader(readerProcess.getInputStream()));
		String l[] = br.readLine().split(":");
		readerProcess.destroy();
		ci.xclass = l[0];
		ci.program = l[1];

		clientInfo.put(idString, ci);

		return ci;
	}

	public void followEvents() throws IOException {
		Process eventReaderProcess = new ProcessBuilder("wmiir", "read", "/event").start();
		BufferedReader eventStream = new BufferedReader(new InputStreamReader(eventReaderProcess.getInputStream()));
		String line;
		long sparkReconnectTime = 1;
		long dbReconnectTime = 1;
		while ((line = eventStream.readLine()) != null) {
			String event[] = line.split(" ");

			// TODO would be nice to retry delivering the message on reconnect

			// (re)connect if necessary
			if (dbReconnectTime != 0 &&
				System.currentTimeMillis() > dbReconnectTime) {
				try {
					databaseInit();
					dbReconnectTime = 0;
					log.info("Connected to DB");
				} catch(SQLException ex2) {
					dbReconnectTime = System.currentTimeMillis() + 30000;
					log.log(Level.SEVERE, "Trouble connecting to DB, won't try for thirty seconds", ex2);
				}
			}

			try {
				if (dbReconnectTime == 0)
					writeEventToDb(event);
			} catch(Exception ex) {
				log.log(Level.SEVERE, "Failed to write event to db: " + Arrays.toString(event), ex);
				dbReconnectTime = 1;
			}

			if (sparkReconnectTime != 0 &&
				System.currentTimeMillis() > sparkReconnectTime) {
				try {
					sparkInit();
					sparkReconnectTime = 0;
					log.info("Connected to SPARK");
				} catch(IOException ex2) {
					sparkReconnectTime = System.currentTimeMillis() + 30000;
					log.log(Level.SEVERE, "Trouble connecting to SPARK, won't try for thirty seconds", ex2);
				}
			}

			try {
				if (sparkReconnectTime == 0) // ie we're connected
					sendEventToSpark(event);
			} catch(IOException ex) {
				log.log(Level.SEVERE, "Failed to send event to Spark: " + Arrays.toString(event), ex);
				sparkReconnectTime = 1;
			}
		}
	}

	public static void main(String args[]) throws Exception {
		new WmiiEventFollower().followEvents();
	}
}
