

import org.restlet.*;
import org.restlet.data.*;
import org.restlet.routing.*;

// c.f. ~/sw/restlet-jse-2.1.4/src/org.restlet.example/org/restlet/example/tutorial/Part11_Routing.java
public class RestEvents extends Application {
	public void run() throws Exception {
        Component component = new Component();
        component.getServers().add(Protocol.HTTP, 9003);
        //component.getClients().add(Protocol.FILE);
        component.getDefaultHost().attach(this);
        component.start();
	}

    @Override
    public Restlet createInboundRoot() {
        Router router = new Router(getContext());

        Restlet eventHandler = new Restlet() {
            @Override
            public void handle(Request request, Response response) {
				Form f = new Form(request.getEntity());
				String id = request.getAttributes().get("id").toString();
				String title = f.getFirstValue("title");
				String url = f.getFirstValue("url");
				String method = request.getResourceRef().getLastSegment();
				if ("activate".equals(method)) {
					System.out.printf("TAB-ACTIVATE %s%n\ttitle=%s%n\turl=%s%n", id, title, url);
				} else if ("urlChange".equals(method)) {
					System.out.printf("TAB-URL-CHANGE %s%n\ttitle=%s%n\turl=%s%n", id, title, url);
				} else if ("content".equals(method)) {
					//System.out.println(f.getFirstValue("content"));
					System.out.println("content ignored");
				} else {
					System.err.println("Unknown method: " + method);
				}
				response.setStatus(Status.SUCCESS_NO_CONTENT);
            }
        };

        router.attach("/chrome/tab/{id}/urlChange", eventHandler);
        router.attach("/chrome/tab/{id}/activate", eventHandler);
        router.attach("/chrome/tab/{id}/content", eventHandler);

        return router;
    }

	public static void main(String args[]) throws Exception {
		System.setProperty("java.util.logging.config.file",
						   "/home/jbalint/sw/spark-1.0.0/src/jess/j.u.logging.properties");
		new RestEvents().run();
	}
}
