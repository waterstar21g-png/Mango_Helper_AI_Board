//var port = chrome.runtime.connect()

// var extensionIds = [
//   ["themango1", "ekmjafhegdcamecbbjgoilfhbbgecpni"],
//   ["themango2", "mdgjiogilpgmidncndjeahahkppnedgj"],
//   ["themango3", "mipehbnncpgjdipmgnofopppgdacpeal"]
// ];


// var dup = 0;
// extensionIds.forEach(function(extension) {

//   chrome.management.get(extension[1], function(result) {

// 	  if(chrome.runtime.lastError) {
// 		//console.log("Whoops.. ");
// 	  } else {
		
// 		dup ++;

// 	  }

// 	  if(dup >1) {

// 		var dup_extenstion = document.querySelector('#dup_extenstion');
// 		dup_extenstion.style.display = "block";

// 	  }

//   });
// });


chrome.runtime.onMessage.addListener(function(request, sender) {
	if (request.action == "getSource") {
		var message = document.querySelector('#result_msg');
		message.innerText = " → "+request.source;
		message.style.color = "blue";
		message.style.fontWeight = "bold";

	}
});



document.addEventListener('DOMContentLoaded', function() {

	var link = document.getElementById('sync_set');

	link.addEventListener('click', function() {

		var site_url = $("#site_url").val();
		site_url = site_url.trim();
		
		var match = site_url.match(/tmg(\d+)\./);
		var client_seq = "";

		if(match && match[1]) {
		
			client_seq =  match[1];
			var client_seq_num = parseInt(client_seq, 10);

			if(client_seq_num>100) {

				if (client_seq_num > 3000) {
					
					if(site_url.indexOf(".mycafe24.") != -1) {}
					else if(site_url.indexOf(".cafe24.") != -1) {
						site_url = site_url.replace(".cafe24.",".mycafe24.");
						$("#site_url").val(site_url);
					}

				} else {

					if(site_url.indexOf(".cafe24.") != -1) {}
					else if(site_url.indexOf(".mycafe24.") != -1) {
						site_url = site_url.replace(".mycafe24.",".cafe24.");
						$("#site_url").val(site_url);
					}
				}
			}
		}

		else {

			if(site_url.indexOf("scrap7.") != -1) {
				if(site_url.indexOf(".cafe24.") != -1) {}
				else if(site_url.indexOf(".mycafe24.") != -1) {
					site_url = site_url.replace(".mycafe24.",".cafe24.");
					$("#site_url").val(site_url);
				}			
			}
			
			if(site_url.indexOf("scrap9.") != -1) {
				if(site_url.indexOf(".mycafe24.") != -1) {}
				else if(site_url.indexOf(".cafe24.") != -1) {
					site_url = site_url.replace(".cafe24.",".mycafe24.");
					$("#site_url").val(site_url);
				}				
			}
		}

		var site_key = $("#site_key").val();
		site_key = site_key.trim();

		chrome.storage.local.set({'site_url': site_url});
		chrome.storage.local.set({'site_key': site_key});
		
		chrome.storage.sync.set({'site_url_sync': site_url});
		chrome.storage.sync.set({'site_key_sync': site_key});


		if(site_url) {

			if(site_url.indexOf("http") != -1){}
			else {
				alert("서비스 URL은 http로 시작되는 URL입니다.\n서비스 URL은 [환경설정]-[서비스정보]-[서비스URL]에서 확인 가능합니다.");
				return;
			}
		}
		

		if(site_url && site_key) {}
		else {
			alert("서비스 URL과 서비스 인증 KEY 모두 입력해주세요.\n서비스 URL 및 서비스 인증 KEY는 [환경설정]-[서비스정보]에서 확인 가능합니다.");
			return;

		}

		
		//onWindowLoad(site_url, site_key);

		var message = document.querySelector('#sync_set');
		message.innerText = "설정값이 저장되었습니다.";
		message.className = "btn btn-primary btn-block";
		

	});

	var link2 = document.getElementById('send_data');
	link2.addEventListener('click', function() {
		
		var site_url = $("#site_url").val();
		site_url = site_url.trim();

		sendTheMango();


	});

	
});

function changeONOFF() {
	var onoff_v = $("#onoff").is(":checked");

	if(onoff_v) {

		chrome.storage.local.set({'onoff': 'off'});
		chrome.storage.sync.set({'onoff_sync': 'off'});

	} else {
		
		chrome.storage.local.set({'onoff': 'on'});
		chrome.storage.sync.set({'onoff_sync': 'on'});


	}

}

function sendTheMango() {

	chrome.tabs.query({active: true, lastFocusedWindow: true}, tabs => {

		var url = tabs[0].url;
		
		var timestamp = new Date().getTime();
		var mango_param = "pmode=mango&smode=detail&tmg_tp=D"+timestamp;

		if(url.indexOf("?") != -1) var ext_url = url + "&"+mango_param;
		else var ext_url = url + "?"+mango_param;

		var site_url = $("#site_url").val();
		site_url = mango_site_url(site_url);

//		if( url.indexOf("detail.tmall.com/item.htm") != -1 ) {
//
//			var site_url = $("#site_url").val();
//			site_url = mango_site_url(site_url);
//			
//			ext_url = ext_url.replace("detail.tmall.com/item.htm","detail.tmall.com/item_o.htm");
//			ext_url = site_url+"mall/admin/shop/extGoodsPop.php?url="+encodeURIComponent(ext_url);
//			
//		}

		var pop_width = "800";
		var pop_height = "700";
		if( url.indexOf("ralphlauren.") != -1 ) {
			pop_width = "1024";
			pop_height = "700";
		}



		var open_extension_name = "open_extension";
		if( url.indexOf("kream.co.kr") != -1 ) open_extension_name = "open_extension_kream_kr_D";
		else if( url.indexOf("tactics.com") != -1 ) open_extension_name = "open_extension_tactics_D";
		else if( url.indexOf("tmall.com") != -1 ) open_extension_name = "open_extension_taobao_D";

		if( url.indexOf("11st.co.kr") != -1 || url.indexOf("tactics.com") != -1 || url.indexOf("summitracing.com") != -1 ||  url.indexOf("design-bestseller.de") != -1 || url.indexOf("kream.co.kr") != -1 || url.indexOf("gap.com") != -1 || url.indexOf("gapfactory.com") != -1 || url.indexOf("salomon.com") != -1 || url.indexOf("selfridges.com") != -1 || url.indexOf("sportsdirect.com") != -1 || url.indexOf("maisonkitsune.com") != -1) {

			ext_url = site_url+"mall/admin/shop/extGoodsPop.php?"+mango_param+"&url="+encodeURIComponent(url);
			pop_extension = window.open(ext_url,  open_extension_name+timestamp,"width="+pop_width+",height="+pop_height+",toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=no");

		} 
		
		else if (url.indexOf("tmall.com") != -1 || url.indexOf("musinsa.com") != -1 ) {
			ext_url = site_url+"mall/admin/shop/extGoodsPop.php?url="+encodeURIComponent(ext_url);
			pop_extension = window.open(ext_url,  open_extension_name+timestamp,"width="+pop_width+",height="+pop_height+",toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=no");

		}

		else {

			pop_extension = window.open(ext_url, open_extension_name+timestamp,"width="+pop_width+",height="+pop_height+",toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=no");
		}

		

	});



}


function checkSiteConfig(site_url) {

	site_url = mango_site_url(site_url);
	var url = site_url + "mall/admin/shop/extGetSiteConfig_D.php";
	var ret = "설정파일을 가져오는데 실패했습니다. 서비스 URL 이 올바른지 확인해보시기 바랍니다.\n서비스 URL은 [환경설정]-[서비스정보]-[서비스URL]에서 확인 가능합니다.";

	$.ajax({
		type: "POST",
		url: url,
		success: function(x,textStatus) {
			site_config = x;

			if(site_config) {
				chk_site(site_config);
			} else {
				alert(ret);
			}

		},
	   error: function(request,status,error){

		var error_code = request.status;
		if(error_code == "404") {
				ret += "\n더망고 익스텐션의 [더망고 서비스 URL] 이 잘못되었습니다.\n서비스 URL은 [환경설정]-[서비스정보]-[서비스URL]에서 확인 가능합니다.";
			} else {
				ret += error;
			}

			alert(ret);
	   }
	 });
}

function chk_site(site_config) {

	chrome.tabs.query({active: true, lastFocusedWindow: true}, tabs => {

		var url = tabs[0].url;
			
		var array_site_config = jQuery.parseJSON(site_config);


		if( chk_config_site(array_site_config, url) ) {

			//url =  url.replace(/\'/g, "%27");
			sendTheMango();


		} else {
			alert("상품데이터 전송을 지원하지 않는 사이트입니다.");
		}

	});



}