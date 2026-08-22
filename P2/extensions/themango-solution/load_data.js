function get_data() {
	var site_url;
	var site_key;
	var onoff;

//	chrome.storage.sync.get({'site_url_sync':'','site_key_sync':'','onoff_sync':''}, function(result) {
//		site_url = result.site_url_sync;
//		site_key = result.site_key_sync;
//		onoff = result.onoff_sync;
//
//		$("#site_url").val(site_url);
//		$("#site_key").val(site_key);
//
//
//
//		if(onoff == "off") {
//			$('#onoff').bootstrapToggle('off')
//
//
//		}
//		else {
//			$('#onoff').bootstrapToggle('on')
//
//		}
//
//    });
	chrome.storage.local.get({'site_url':'','site_key':'','onoff':''}, function(result) {
		site_url = result.site_url;
		site_key = result.site_key;
		onoff = result.onoff;

		$("#site_url").val(site_url);
		$("#site_key").val(site_key);



		if(onoff == "off") {
			$('#onoff').bootstrapToggle('off')


		}
		else {
			$('#onoff').bootstrapToggle('on')

		}

    });

}



window.onload = get_data;
