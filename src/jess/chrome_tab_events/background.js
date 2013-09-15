// TODO selecting tabs. c.f. http://stackoverflow.com/questions/16276276/chrome-extension-select-next-tab

// dont think this is useful
// chrome.tabs.onCreated.addListener(function (tab) {
// 	console.log("TAB CREATED");
// 	console.log(tab.id);
// 	console.log(tab);
// });

function isInspectableUrl(url) {
	return url.indexOf("http") == 0 ||
		url.indexOf("file") == 0;
}

chrome.tabs.onActivated.addListener(function (activeInfo) {
	chrome.tabs.get(activeInfo.tabId, function (tab) {
		if (!isInspectableUrl(tab.url))
			return;
		console.log("TAB-ACTIVATE " + activeInfo.tabId);
		console.log("\ttitle=" + tab.title);
		console.log("\turl=" + tab.url);
		//console.log(activeInfo);
	});
});

chrome.tabs.onUpdated.addListener(function (tabId, changeInfo, tab) {
	if (!isInspectableUrl(tab.url))
		return;
	if (changeInfo.url) {
		console.log("TAB-URL-CHANGE " + tabId);
		console.log("\turl=" + tab.url);
	}
	//console.log(changeInfo);

	// when page has loaded get the content
	if (changeInfo.status == "complete") {
		// skip is not {found,available}
		if (tab.title.indexOf(tab.url + " is not ") == 0)
			return;
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
});
