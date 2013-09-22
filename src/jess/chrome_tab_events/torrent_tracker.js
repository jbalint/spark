
// the code to be injected into the running tab
function getEpisodes(ezTvUrl, showId) {
	function extractEp(el) {
		return {ep: $("td a.epinfo", el).text(),
				magnetURL: $("td a.magnet", el).attr("href")}
	}
	var eps = $.map(jQuery("tr.forum_header_border[name='hover']"), function (el, idx) {
		return extractEp(el);
	});
	chrome.runtime.sendMessage({type:'torrentMagnetLinks',
								ezTvUrl: ezTvUrl,
								showId: showId,
								eps: eps
							   });
}

function getTorrents(ezTvUrl, showId) {
	// globalize values
	window["ezTvUrl"] = ezTvUrl;
	window["showId"] = showId;

	// generate code to run in temp tab
	var code = getEpisodes + " \n getEpisodes('" + ezTvUrl + "' , " + showId + ");";

	// being process
	runCodeInTempTab(ezTvUrl, code);
}

chrome.runtime.onMessage.addListener(function (message, sender) {
	if (message.type == 'torrentMagnetLinks') {
		postEvent(sender.tabId, 'torrentMagnetLinks', message);
	}
});
