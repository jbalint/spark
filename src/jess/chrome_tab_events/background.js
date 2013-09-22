// public API:

// postEvent(tabId, method, data)
// runCodeInTempTab(url, code)


// TODO selecting tabs. c.f. http://stackoverflow.com/questions/16276276/chrome-extension-select-next-tab

// dont think this is useful
// chrome.tabs.onCreated.addListener(function (tab) {
// 	mylog("TAB CREATED");
// 	mylog(tab.id);
// 	mylog(tab);
// });

function mylog(msg) {
	if (true) {
		if (typeof msg == 'string') {
			console.log(msg.substr(0, 100));
		} else {
			console.log(msg);
		}
	}
}

function mywarning(msg) {
	console.log("WARNING: " + msg);
}

// open web socket to communicate with server
// c.f. http://blog.chromium.org/2009/12/web-sockets-now-available-in-google.html
var connectFailCount = 0;
var msToNextConnect = 0;
var ws = {};

function wsOnMessage(evt) {
	var msg = evt.data;
	if (msg.indexOf("js: ") == 0) {
		eval(msg.substr(4));
	} else {
		mylog("Unhandled WS message: " + msg);
	}
}

function wsOnOpen() {
	connectFailCount = 0;
	msToNextConnect = 0;
}

function wsOnClose() {
	wsConnectTimer(msToNextConnect);
	msToNextConnect += 10000;
}

function wsConnectReal() {
	if (ws.readyState == 1) {
		mylog("websocket already connected");
		return;
	}
	try {
		ws = new WebSocket("ws://localhost:9004");
	} catch (e) {
		mywarning(e);
		wsConnectTimer(msToNextConnect);
		msToNextConnect += 20000;
		return;
	}
	ws.onmessage = wsOnMessage;
	ws.onopen = wsOnOpen;
	ws.onclose = wsOnClose;
}

function wsConnectTimer(time) {
	setTimeout(wsConnectReal, time);
}

function wsChecker() {
	if (ws.readyState != 1) {
		mylog("Connecting websocket");
		wsConnectReal();
	}
	setTimeout(wsChecker, 60 * 1000);
}

function isInspectableUrl(url) {
	return url.indexOf("http") == 0 ||
		url.indexOf("file") == 0;
}

function postEvent(tabId, method, data) {
	var evt = {}
	evt.tabid = tabId;
	evt.type = method;
	evt.data = data;
	if (ws.readyState != 1) {
		mywarning("Event lost. websocket not connected");
		return;
	}
	var txt = JSON.stringify(evt);
	mylog("Sending: " + txt);
	ws.send(txt);

// from old "Restlet" version (one-way comm only)
//var urlPrefix = "http://localhost:9003/chrome/tab/";
//	jQuery.ajax(urlPrefix + tabId + "/" + method,
//				{data: data, dataType: "text", type: "POST"});
}

wsChecker();

chrome.tabs.onActivated.addListener(function (activeInfo) {
	chrome.tabs.get(activeInfo.tabId, function (tab) {
		if (tab.id == automatedProcessTabId) {
			mylog("Dont do anything for automated process tab");
			return;
		}
		if (!isInspectableUrl(tab.url))
			return;
		mylog("TAB-ACTIVATE " + activeInfo.tabId);
		mylog("\ttitle=" + tab.title);
		mylog("\turl=" + tab.url);
		//mylog(activeInfo);
		var params = {};
		params.title = tab.title;
		params.url = tab.url;
		postEvent(tab.id, "activate", params);
	});
});

chrome.tabs.onUpdated.addListener(function (tabId, changeInfo, tab) {
	if (!isInspectableUrl(tab.url))
		return;

	// when page has loaded get the content
	if (changeInfo.status == "complete") {
		// skip is not {found,available}
		if (tab.title.indexOf(tab.url + " is not ") == 0)
			return;

		if (tabId == automatedProcessTabId) {
			automatedProcessTabId = -1;
			automatedProcessLoadCallback(tabId, changeInfo, tab);
			return;
		}

		mylog("TAB-URL-CHANGE " + tabId);
		mylog("\turl=" + tab.url);

		// post the event
		var params = {};
		params.title = tab.title;
		params.url = tab.url;
		postEvent(tab.id, "urlChange", params);

		// get the content
		var injectD = {};
		injectD.allFrames = true;
		//injectD.code = "chrome.runtime.sendMessage({content: document.documentElement.innerHTML});";
		injectD.code = "chrome.runtime.sendMessage({type: 'bodyText', content: document.body.textContent});";
		chrome.tabs.executeScript(tabId, injectD);
	}
});

// http://developer.chrome.com/extensions/messaging.html
// http://developer.chrome.com/extensions/runtime.html#event-onMessage
chrome.runtime.onMessage.addListener(function (message, sender) {
	//mylog("onMessage: from tab: " + sender.tab.id);
	//mylog(message);
	//mylog(sender);
	if (message.type == 'bodyText') {
		var params = {};
		params.content = message.content;
		//postEvent(sender.tab.id, "content", params);
	}
});

function automatedProcessLoadCallback(tabId, changeInfo, tab) {
	chrome.tabs.executeScript(tabId, {file: "jquery.min.js"}, function () {
		chrome.tabs.executeScript(tabId, {code: automatedProcessCode}, function () {
			chrome.tabs.remove(tabId);
		});
	});
}

var automatedProcessTabId = -1;
var automatedProcessCode = null;

function setAutomatedProcessTab(tab) {
	automatedProcessTabId = tab.id;
}

function runCodeInTempTab(url, code) {
	var props = {};
	props.active = false;
	props.url = ezTvUrl;
	automatedProcessCode = code;
	chrome.tabs.create(props, setAutomatedProcessTab);
}
