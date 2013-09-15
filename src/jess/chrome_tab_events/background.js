// TODO selecting tabs. c.f. http://stackoverflow.com/questions/16276276/chrome-extension-select-next-tab

// dont think this is useful
// chrome.tabs.onCreated.addListener(function (tab) {
// 	console.log("TAB CREATED");
// 	console.log(tab.id);
// 	console.log(tab);
// });

var urlPrefix = "http://localhost:9003/chrome/tab/";

function isInspectableUrl(url) {
	return url.indexOf("http") == 0 ||
		url.indexOf("file") == 0;
}

function post(tabId, method, data) {
	jQuery.ajax(urlPrefix + tabId + "/" + method,
				{data: data, dataType: "text", type: "POST"});
}

chrome.tabs.onActivated.addListener(function (activeInfo) {
	chrome.tabs.get(activeInfo.tabId, function (tab) {
		if (!isInspectableUrl(tab.url))
			return;
		console.log("TAB-ACTIVATE " + activeInfo.tabId);
		console.log("\ttitle=" + tab.title);
		console.log("\turl=" + tab.url);
		//console.log(activeInfo);
		var params = {};
		params.title = tab.title;
		params.url = tab.url;
		post(tab.id, "activate", params);
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

		console.log("TAB-URL-CHANGE " + tabId);
		console.log("\turl=" + tab.url);

		// post the event
		var params = {};
		params.title = tab.title;
		params.url = tab.url;
		post(tab.id, "urlChange", params);

		// get the content
		var injectD = {};
		injectD.allFrames = true;
		injectD.code = "chrome.runtime.sendMessage({content: document.documentElement.innerHTML});";
		chrome.tabs.executeScript(tabId, injectD);
	}
});

// http://developer.chrome.com/extensions/messaging.html
// http://developer.chrome.com/extensions/runtime.html#event-onMessage
chrome.runtime.onMessage.addListener(function (message, sender) {
	//console.log("onMessage: from tab: " + sender.tab.id);
	//console.log(message);
	//console.log(sender);
	var params = {};
	params.content = message.content;
	post(sender.tab.id, "content", params);
});
