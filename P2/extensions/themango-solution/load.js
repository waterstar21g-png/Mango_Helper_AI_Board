var g_mango_refer = document.referrer;
var g_now_url = "";
var g_image_set = new Array();
var g_image_data;
var g_en_type = "";
var g_onload_count = 0;
var g_onload_sleep = 0; //로직 끝나고 최종 전송까지 대기시간
var g_onload_top = ""; //데이터 전송전에 최상단으로 스크롤 이동 후 전송
var g_debug = "";
var g_direct_send = "";
var g_pop_name = window.name;
var g_check_data = ""; //global 변수가 필요할때 사용
var g_check_data2 = ""; //global 변수가 필요할때 사용
var g_check_data3 = ""; //global 변수가 필요할때 사용
var g_check_data_int = 0; //global 변수가 필요할때 사용
var g_check_data_int2 = 0; //global 변수가 필요할때 사용
var g_check_data_array = new Array();
var g_image_url;
var g_not_found = "";
var g_extension_site_id = "";

//var tab_id; 미사용
//global 사용X
var pmode = "mango";
var smode;
var tmg_tp;
var tmg_guid;
var tmg_sruid;
var tmg_cnt = "";
var load_count = 0;
var scroll_end_check = new Array();
var send_tmg;
var site_url;
var site_key;
var search2_end;



//global 복잡
var tab_url = "";
var html_source;
var item_count = 0; 
var option_count = 0; 



//console.log("==> 맨위 g_onload_count :"+g_onload_count);
// alert(tab_url);


// chrome.runtime.sendMessage({ type: "GET_WINDOW_ID" }, (response) => {
// 	alert("win:" + response.windowId);
//   });

// chrome.storage.local.set({tab_url: ''});
chrome.storage.local.remove(tab_url);




// alert("g_pop_name11: "+g_pop_name);


  // 세션스토리지에서 현재 탭의 url 값을 가져오기
//   function loadUrlFromSession() {
	// chrome.runtime.sendMessage({ type: "GET_CONTEXT" }, async (ctx) => {
	//   const storageKey = `${ctx.windowId}_${ctx.tabId}`;
  
	//   const items = await chrome.storage.session.get(storageKey);
	//   const value = items[storageKey];
  
	//   alert("value" + value);
	// //   if (typeof value !== "undefined") {
	// // 	await chrome.storage.session.remove(storageKey); // 읽고 즉시 삭제
	// //   }

	// });
//   }


async function consumeFromLocalStorageAsync() {

	const ctx = await new Promise((resolve) =>
	  chrome.runtime.sendMessage({ type: "GET_CONTEXT" }, resolve)
	);
  
	const storageKey = `ctx:${ctx.windowId}_${ctx.tabId}`;
//   alert(storageKey);
	const res = await new Promise((resolve) =>
	  chrome.storage.local.get(storageKey, resolve)
	);


	const val = res[storageKey];
	await cleanupExpiredCtxKeys();

	if (val !== undefined) {

		const finalURL = val?.finalURL;

		await chrome.storage.local.remove(storageKey);
		return finalURL;
	}

	return "";
}
 
// 초기화 후 → 이후 코드 실행
async function initTabUrlAndContinue() {

	tab_url = await consumeFromLocalStorageAsync();


	//스토리지 에 값이 있으면
	if(tab_url) preload();
	else {



		if (g_mango_refer.indexOf("pmode%3Dmango") != -1 || g_mango_refer.indexOf("pmode=mango") != -1) { 

			if (g_mango_refer.indexOf("extGoodsPop.php") != -1) { 
				
				var param = getUrlParams(g_mango_refer);
				tab_url = decodeURIComponent(param.url);
		//console.log(tab_url);

		//alert(tab_url);
		// console.log("=22=> tab_url : "+tab_url);

				tmg_tp = param.tmg_tp;
				pmode = param.pmode;
				smode = param.smode;
				tmg_cnt = param.tmg_cnt;
				tmg_sruid = param.tmg_sruid;
				tmg_guid = param.tmg_guid;
				
				if(pmode) tab_url += "&pmode="+pmode;
				if(smode) tab_url += "&smode="+smode;
				if(tmg_tp) tab_url += "&tmg_tp="+tmg_tp;
				if(tmg_cnt) tab_url += "&tmg_cnt="+tmg_cnt;
				if(tmg_sruid) tab_url += "&tmg_sruid="+tmg_sruid;
				if(tmg_guid) tab_url += "&tmg_guid="+tmg_guid;

				g_now_url = window.location.href;

			}
			else {
				tab_url = g_mango_refer;
				g_now_url = window.location.href;
			}
			
			preload();



		//	chrome.storage.local.set({tab_url: ''});
		//	chrome.storage.local.set({'tab_url': tab_url});

		}
		else {


			tab_url = window.location.href; 

			//alert(tab_url);
			//alert(g_pop_name);
			if( tab_url.indexOf("pmode=mango") != -1 &&  tab_url.indexOf("tmg_tp") != -1  ) {
				
				if(tab_url.indexOf("aliexpress.com") != -1 && tab_url.indexOf("smode=search") != -1 ) {
					
					if(g_pop_name.indexOf("?") != -1 && g_pop_name.indexOf("open_extension") != -1) {
						var ppp = g_pop_name.match( /open\_extension(.*?)\?/si  );
						g_pop_name = "open_extension"+ppp[1];
			
						chrome.storage.local.get({[g_pop_name]:''}, function(result) {

		//					eval("tab_url = result."+g_pop_name);
							var __tab_url = result[g_pop_name];
							if(__tab_url) tab_url = decodeURIComponent(tab_url);

							chrome.storage.local.remove([g_pop_name], function() {
								preload();
							});

							// preload();

						});

					} else preload();


				}
		
				else preload();

			} else if(tab_url.indexOf("error.item.taobao.com/error/noitem") != -1 ) {
				// 타오바오 삭제페이지로 이동하는 경우.
				g_not_found = "Y";
				
				var ppp = g_pop_name.match( /open\_extension(.*?)\?/si  );
				tmg_tp = "open_extension"+ppp[1];

				tab_url = "http://www.taobao.com/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;
				preload();

			} else {
				
		//		if( tab_url.indexOf("brand.naver.com") != -1 ) {
		//console.log("==> 111111111111111111111111111");
		//			// 2. inject.js 주입
		//			const script = document.createElement("script");
		//			script.src = chrome.runtime.getURL("inject2.js");
		//			(document.head || document.documentElement).appendChild(script);
		//			script.remove();
		//		}

	// alert("g_pop_name: "+g_pop_name+" /// tab_url : "+tab_url);
				if(g_pop_name.indexOf("open_extension") != -1) {
					//여러번 리다이렉션 되는 사이트 품절처리
					if( ( g_pop_name.indexOf("?") != -1 && g_pop_name.indexOf("1688_") != -1) ) {
						
						g_not_found = "Y";

						var ppp = g_pop_name.match( /open\_extension(.*?)\?/si  );
						
						tmg_tp = "open_extension"+ppp[1];
						tab_url = "https://detail.1688.com/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;
						preload();

					} else if(tab_url.indexOf("//www.gmarket.co.kr") != -1 && g_pop_name.indexOf("gmarket_") != -1) {

						g_not_found = "Y";

						//var ppp = g_pop_name.match( /open\_extension\_detail\_gmarket_kr\_(.+)/si  );
						//tmg_tp = ppp[1];
						tmg_tp = g_pop_name;
						

						tab_url = "http://www.gmarket.co.kr/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;
						if(g_pop_name.indexOf("gmarket_smile") != -1) tab_url = "http://www.gmarket.co.kr/n/SmileDelivery/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} else if(tab_url.indexOf("auction.co.kr") != -1 && g_pop_name.indexOf("auction_") != -1) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;
						
						tab_url = "http://www.auction.co.kr/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;
						if(g_pop_name.indexOf("auction_smile") != -1) tab_url = "http://www.auction.co.kr/n/SmileDelivery/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} else if(tab_url.indexOf("product-not-available") != -1 && g_pop_name.indexOf("puma_kr_") != -1) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;
						
						tab_url = "https://kr.puma.com/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} else if(tab_url.indexOf("/list.html") != -1 && g_pop_name.indexOf("footsell_kr_") != -1) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "http://www.footsell.co.kr/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();
					} else if(g_pop_name.indexOf("tennis_point_") != -1 ) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "http://www.tennis-point.com/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} 
					
					else if(g_pop_name.indexOf("sivillage_") != -1 ) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "http://www.sivillage.com/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} 

					else if(g_pop_name.indexOf("uniqlo_jp_") != -1 ) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "http://www.uniqlo.com/jp/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} 

					else if(g_pop_name.indexOf("uniqlo_kr_") != -1 ) {

						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "https://www.uniqlo.com/kr/ko/product-not-found?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} 

					else if(g_pop_name.indexOf("mustit_kr_") != -1 && tab_url == "https://m.web.mustit.co.kr/?baselayer=y" ) {	// 판매종료된 상품은 https://m.web.mustit.co.kr/?baselayer=y 로 이동됨.
			
						g_not_found = "Y";

						tmg_tp = g_pop_name;

						tab_url = "http://m.web.mustit.co.kr/not_found.html?pmode=mango&smode=detail&tmg_tp="+tmg_tp;

						preload();

					} 


					//품절처리는 2024.1.6 이후에는 newbalance 로직으로 이용함.
					//품절만 리다이렉션 되는 경우는 위 로직으로 품절처리하면 되고, 정상 상품인데 리다이렉션 되는 경우는 아래 로직이용하면 됨. 2024.5.23

					else if(g_pop_name.indexOf("kream_kr") != -1) {


						if(g_pop_name.indexOf("_detail_") != -1 || g_pop_name.indexOf("kream_kr_D") != -1) {

							var pop_exp = g_pop_name.split("_kream_kr_");
							g_now_url = window.location.href;
							tab_url = g_now_url + "?pmode=mango&smode=detail&tmg_tp="+pop_exp[1];
							
						} 
						else if(g_pop_name.indexOf("_detailsearch_") != -1) {

							var pop_exp = g_pop_name.split("_kream_kr_");
							g_now_url = window.location.href;
							tab_url = g_now_url + "?pmode=mango&smode=detail_search&tmg_tp="+pop_exp[1];
							
						}
						else {

							var pop_exp = g_pop_name.split("_kream_kr_");
							var pop_exp2 = pop_exp[1].split("|");

							if(pop_exp2[2] == "undefined") pop_exp2[2] = "";

							g_now_url = window.location.href;
							if(pop_exp2[1] == "1") tab_url = g_now_url + "?pmode=mango&smode=search"+pop_exp2[1]+"&tmg_tp="+pop_exp2[0];
							else tab_url = g_now_url + "?pmode=mango&smode=search"+pop_exp2[1]+"&tmg_tp="+pop_exp2[0]+"&tmg_cnt="+pop_exp2[2]+"&tmg_sruid="+pop_exp2[3];

							tmg_cnt = pop_exp2[2];


						}

						preload();

					} else if(g_pop_name.indexOf("tactics") != -1) {

						tab_url = use_pop_name("tactics");
						preload();

					} 
					
					else if(g_pop_name.indexOf("newbalance") != -1) {

						tab_url = use_pop_name("newbalance");
						preload();

					} 

					else if(g_pop_name.indexOf("jentestore") != -1) {

						tab_url = use_pop_name("jentestore");
						preload();

					} 

					else if(g_pop_name.indexOf("balaan_kr") != -1) {

						tab_url = use_pop_name("balaan_kr");
						preload();

					} 

					// else if(g_pop_name.indexOf("halfclub") != -1) {

					// 	tab_url = use_pop_name("halfclub");
					// 	alert(tab_url);
					// 	preload();

					// } 
					else {


						if(g_pop_name.indexOf("open_extension") != -1 && g_pop_name.indexOf("nameStorage:") != -1 ) {
							
							var pop_name_match = g_pop_name.match( /nameStorage:(.*?)\?/ );
							g_pop_name = pop_name_match[1];

						}
						

						if(g_pop_name.indexOf("open_extension") != -1 && g_pop_name.indexOf("|") != -1) {
							var pop_exp = g_pop_name.split("|");
							g_pop_name = pop_exp[0];
						}

						chrome.storage.local.get({[g_pop_name]:''}, function(result) {
		//					eval("tab_url = result."+g_pop_name);
							tab_url = result[g_pop_name];
							tab_url = decodeURIComponent(tab_url);

							chrome.storage.local.remove([g_pop_name], function() {
								preload();
							});

							// preload();

						});
					}

				} else preload();

			}
		}
	}
}
  
  // 초기 시작점
initTabUrlAndContinue();


	

function use_pop_name(site_id, type="") {


	var pop_exp = g_pop_name.split("_"+site_id+"_");
	g_now_url = window.location.href;

	if(g_pop_name.indexOf("_detail_") != -1 || g_pop_name.indexOf(site_id+"_D") != -1) {

		tab_url = g_now_url + "?pmode=mango&smode=detail&tmg_tp="+pop_exp[1];
		
	} 
	else if(g_pop_name.indexOf("_detailsearch_") != -1) {

		tab_url = g_now_url + "?pmode=mango&smode=detail_search&tmg_tp="+pop_exp[1];
		
	}
	else {

		var pop_exp2 = pop_exp[1].split("|");

		if(pop_exp2[2] == "undefined") pop_exp2[2] = "";

		if(pop_exp2[1] == "1") tab_url = g_now_url + "?pmode=mango&smode=search"+pop_exp2[1]+"&tmg_tp="+pop_exp2[0];
		else tab_url = g_now_url + "?pmode=mango&smode=search"+pop_exp2[1]+"&tmg_tp="+pop_exp2[0]+"&tmg_cnt="+pop_exp2[2]+"&tmg_sruid="+pop_exp2[3];

		tmg_cnt = pop_exp2[2];

	}
	return tab_url;

}


function preload() {

	chrome.storage.local.remove([g_pop_name]);
//	chrome.storage.local.set({[g_pop_name]: ''});

// alert("preload:"+tab_url);
//console.log("==> preload "+tab_url);

//alert("preload");
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	/////////////////	                                                                                                                                                          /////////////////
	/////////////////	                                                                                                                                                          /////////////////
	/////////////////	                        https://premium-dot-acp-magento.appspot.com/ api 서버, labelleperfumes.com                          /////////////////
	/////////////////	                                                                                                                                                          /////////////////
	/////////////////	                                                                                                                                                          /////////////////
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	if(tab_url.indexOf("appspot.com") != -1 || tab_url.indexOf("labelleperfumes.com") != -1) {

		tab_url =  tab_url.replace("tmg-tp=", "tmg_tp=");

	}


	//상세페이지에서 직접 저장하는 경우
	if( tab_url.indexOf("tmg_tp=D") != -1 || tab_url.indexOf("tmg_tp=d") != -1 || tab_url.indexOf("tmg_tp%3DD") != -1) {
		
		g_direct_send = "Y";

	} 
	
	else if( tab_url.indexOf("tmg_tp=g_debug") != -1 ) {
		
		g_debug = "Y";

	}



// 	if( (tab_url.indexOf("cafe24.com/") != -1 || tab_url.indexOf(".themango.co.kr/") != -1 ) && ( tab_url.indexOf("admin_goods_update.php") != -1 || tab_url.indexOf("getGoods.php") != -1 || tab_url.indexOf("getGoodsCategory.php") != -1 || tab_url.indexOf("getList.php") != -1 ) )  {

// 		chrome.storage.local.get({'site_url':'','site_key':'','onoff':'','tab_url':'', 'site_config':''}, function(result) {
// 			site_url = result.site_url;
// 			site_key = result.site_key;

// 			if(!site_url) {
// 				alert("더망고 익스텐션의 [더망고 서비스 URL] 이 입력되지 않았습니다.\n서비스 URL 은 [환경설정] 메뉴에서 확인이 가능합니다.");
// 				return;
// 			}

// 			if(!site_key) {
// 				alert("더망고 익스텐션의 [서비스 인증 KEY] 가 입력되지 않았습니다.\서비스 인증 KEY 는 [환경설정] 메뉴에서 확인이 가능합니다.");
// 				return;
// 			}
			
			
// 			var site_url2 = site_url.replace("http://", "");
// 			var site_url2 = site_url2.replace("https://", "");

// 			if( tab_url.indexOf(site_url2) != -1 ) {
// 				//$("#extension_msg").css("display","none");
// 			}
// 			else {
// 				$("#extension_msg").css("display","");
// 				$("#extension_msg_cont").html("※ 더망고 익스텐션의 [더망고 서비스 URL]이 현재 접속하신 서비스 주소와 일치하지 않습니다. 입력하신 [더망고 서비스 URL] 을 수정해주세요.");
// 				return;
// 			}

// 		});

// 		chrome.runtime.sendMessage('checkPopups');
// //		chrome.runtime.sendMessage('checkVersion');


// 	}

	//새로운 alert 방식 2026.5.8
	if( /\.(my)?cafe24\.|\.themango\.co\.kr\//.test(tab_url) && /(getGoods.*\.php|getList.*\.php|admin_goods_update\.php)/.test(tab_url) )
	{                                                                                         
						
		chrome.storage.local.get({'site_url':'','site_key':'','onoff':''}, function(result) {   
			// client 가 처리할 수 있게 데이터만 주입
			window.postMessage({                                                                
				type: 'THEMANGO_EXT_INFO',                                                 
				site_url: result.site_url || '',                                                
				site_key: result.site_key || '',                                           
				onoff:    result.onoff    || ''                                                 
			}, '*');                                                             
		});                                      
																								
		chrome.runtime.sendMessage('checkPopups');                                         
	}    


	if( (tab_url.indexOf("pmode=mango") != -1 &&  tab_url.indexOf("tmg_tp=") != -1) || ( tab_url.indexOf("pmode%3Dmango") != -1 &&  tab_url.indexOf("tmg_tp%3D") != -1 ) )  {

		if( tab_url.indexOf("amazon.") != -1 || tab_url.indexOf("harrods.com") != -1  || tab_url.indexOf("krollcorp.com") != -1  || tab_url.indexOf("pharmaca.") != -1 || tab_url.indexOf("naver.") != -1) {
			$(document).ready(function(){
				storage_get();
			});
		}
		else if ( tab_url.indexOf("lounge-b.com") != -1 || tab_url.indexOf("birkenstock.com") != -1 || tab_url.indexOf("suksuk.co.kr") != -1 || tab_url.indexOf("coachoutlet.com") != -1 || tab_url.indexOf("shopping.naver.com") != -1 || tab_url.indexOf("nstationmall.com") != -1 || tab_url.indexOf("jcpenney.com") != -1 || tab_url.indexOf("diptyqueparis.com") != -1 || tab_url.indexOf("dollskill.com") != -1 || tab_url.indexOf("trendhunterb2b.com") != -1 || tab_url.indexOf("uniqlo.com/jp") != -1 || tab_url.indexOf("imarket.co.kr") != -1 ||  tab_url.indexOf("academy.com") != -1 || tab_url.indexOf("prodirectsport.") != -1 || tab_url.indexOf("cha9524.com") != -1 || tab_url.indexOf("rebelsport.com.au") != -1 || tab_url.indexOf("11st.co.kr") != -1 || tab_url.indexOf("carrefour.") != -1 ||  tab_url.indexOf("vvic.") != -1 || tab_url.indexOf("timeshop24.") != -1 ||  tab_url.indexOf("gmarket.co.kr") != -1 || tab_url.indexOf("auction.co.kr") != -1 || tab_url.indexOf("alibaba.") != -1 || tab_url.indexOf("taobao.") != -1 || tab_url.indexOf("tmall.") != -1 || tab_url.indexOf("jiyoujia.") != -1 || tab_url.indexOf("jd.com") != -1  || tab_url.indexOf("rakuten.") != -1 || tab_url.indexOf("1688.com") != -1 || tab_url.indexOf("tradeinn.com") != -1 ) {
			storage_get();
		}

		else {
//console.log("==>"+storage_get);
			//window.onload = storage_get;

			if (document.readyState === "complete") {	// json 이 표시되는 사이트의 경우 onload 보다 먼저 끝나서 onload가 실행이 안되는 경우가 있음.
				storage_get();
			} else {
				//window.addEventListener("load", storage_get);
				window.onload = storage_get;
			}

		}

	}

}



function storage_get() {

	chrome.storage.local.get({'site_url':'','site_key':'','onoff':''}, function(result) {

		site_url = result.site_url;
		site_key = result.site_key;
		onoff = result.onoff;

		if(onoff != "off") {

			if(!site_url) {
				alert("더망고 익스텐션의 [더망고 서비스 URL] 이 입력되지 않았습니다.");
				return;
			}

			if(!site_key) {
				alert("더망고 익스텐션의 [서비스 인증 KEY] 가 입력되지 않았습니다.");
				return;
			}

		} else {
			alert("더망고 익스텐션의 [상품수집 ON/OFF] 가 OFF로 설정되어 있습니다.");
			return;
		}

		if(g_onload_count == 0) getImage();

//		getImage();

	});
}



function getImage() {
//console.log("==> getImage ");
	
	g_onload_count++;


	var param = getUrlParams(tab_url);

	tmg_tp = param.tmg_tp;
	tmg_guid = param.tmg_guid;
	pmode = param.pmode;
	smode = param.smode;
	tmg_cnt = param.tmg_cnt;


	//smode=image 일때, 이미지 1개씩 다운로드
	if(tab_url.indexOf("smode=image") != -1 ) {

		g_image_url = $("img").eq(0).attr('src');


		$('body').append("<div id='themango' style='width:800px;'><img width='100%' src="+g_image_url+"></div>");


		html2canvas( document.querySelector('#themango'), { logging: true, letterRendering: 1, useCORS: true } ).then(canvas => { 

//				document.body.appendChild(canvas);
			g_image_data = canvas.toDataURL();

			getImage_next2();

		});
				
	}
	


	else {

		
		if(tab_url.indexOf("caf2.com") != -1 ) {
	//		if(tab_url.indexOf("smode=detail") != -1) {
				
				
	//			var image_cnt = 0;
	//
	//			//$("meta[property='og:image']").each(function(){ //이상한 이미지가 1개 있어서 제외
	//			$("a[data-magic-slide-id='zoom']").each(function(){ 
	//				
	//				g_image_url = $(this).attr('href');
	//				
	//				g_image_set[image_cnt] = g_image_url;
	//				image_cnt++;
	//				
	//			});
	//			
	//
	//			if(!g_image_set[0]) {
	//				g_image_url = $("meta[property='og:image']").eq(0).attr('content');
	//				g_image_set[0] = g_image_url;
	//			}


				//getImage_next();
				//gethtml();

	//			setTimeout(function() {
	//				  gethtml();
	//			}, 3000);


	//				toDataUrl(g_image_url, function(myBase64) {
	//					.ajax {
	//
	//					}
	//
	//					gethtml();
	//				});
	//						
	//						

	//				g_image_url = $("meta[property='og:image']").eq(0).attr('content');
	//
	//				toDataUrl(g_image_url, function(myBase64) {
	//					g_image_data = myBase64;
	//					
	//					gethtml();
	//
	//				});
		
	//		} else gethtml();

			gethtml();
		}






		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                    /gucci/                                                                              /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//		else if(tab_url.indexOf("gucci.com") != -1 ) {
//		
//
//			if(tab_url.indexOf("smode=detail") != -1 ) {
//
//				var id_json = $("script[type='application/ld+json']").html();
//				id_json = id_json.replace(/\n/g, "");
//				id_json = JSON.parse(id_json);
//
//				g_image_url = id_json['image'][0];
//				g_image_url = g_image_url.replace(/[0-9][0-9][0-9]x[0-9][0-9][0-9]/si, "800x800");
//
//				$('body').append("<div id='themango' style='width:800px;text-align:center'><img width='100%' src="+g_image_url+"></div>");
//				
//				html2canvas( document.querySelector('#themango'), { logging: true, letterRendering: 1, useCORS: true } ).then(canvas => { 
//		//				document.body.appendChild(canvas);
//						g_image_data = canvas.toDataURL();
//						gethtml();
//				});
//
//
//			}
//
//			else gethtml();
//
//
//
//	//		toDataUrl(g_image_url, function(myBase64) {
//	//		g_image_data = myBase64;
//	//				
//	//			gethtml();
//	//
//	//		});
//
//
//	//		var image_tmp = id_json['image'];
//	//		$.each(image_tmp, function(index, value) {
//	//
//	//			var value2 = value.replace(/[0-9][0-9][0-9]x[0-9][0-9][0-9]/si, "800x800");
//	//			g_image_set[index] = value2;
//	//		});
//
//			//전체 썸네일 받을 때
//			//getImage_next();
//			
//
//
//		}


		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                    /costco_jp/                                                                       /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		/////////////////	                                                                                                                                                          /////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		else if(tab_url.indexOf("costco.co.jp") != -1 ) {
		

			if(tab_url.indexOf("smode=detail") != -1 ) {

				g_image_url = $("div.zoomImg").find("img").attr('src');

				$('body').append("<div id='themango' style='width:800px;text-align:center'><img width='100%' src="+g_image_url+"></div>");
				
				html2canvas( document.querySelector('#themango'), { logging: true, letterRendering: 1, useCORS: true } ).then(canvas => { 
		//				document.body.appendChild(canvas);
						g_image_data = canvas.toDataURL();
						gethtml();
				});
			}

			else gethtml();


		}

		else {
			
			try { 
				
				gethtml();

			} catch (e) {

				console.error("Mango:", e);
				
				//특정사이트는 현재 보여지는 소스를 전송, 애러처리를 위해
				if(tab_url.indexOf("prodirectsport.com") != -1 ) {}
				else html_source = "<html>THEMANGO_LOADJSERROR</html>";

				get_onload();
			}
									
			
		}

	}

}


function gethtml() {
	//console.log("==> gethtml ");
	//alert("gethtml");

	var param = getUrlParams(tab_url);

	tmg_tp = param.tmg_tp;
	pmode = param.pmode;
	smode = param.smode;
	tmg_cnt = param.tmg_cnt;

	html_source = document.documentElement.outerHTML;
	send_tmg = "Y"; //모든 소스는 전송이 기본값

	if(tab_url.indexOf("smode=") != -1 || tab_url.indexOf("smode%3D") != -1) {
	

		parseSite();


		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		/////////////////                                                                                                              /////////////////
		/////////////////                                                                                                              /////////////////
		/////////////////                                                /소스전송/                                                     /////////////////
		/////////////////                                                                                                              /////////////////
		/////////////////                                                                                                              /////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		if(send_tmg == "Y") {

			if(g_onload_top == "Y") $('html, body').animate({scrollTop : 0}, 0);

			setTimeout(function() {
				
				get_onload();

			}, g_onload_sleep);


		}


	}


}
	


//canvas.js 이미지 보내기
function getImage_next2() {


	chrome.storage.local.get({'site_url':'','site_key':'','onoff':'','tab_url':'', 'site_config':''}, function(result) {
		site_url = result.site_url;
		site_key = result.site_key;

		site_url = mango_site_url(site_url);


		var url = site_url+"mall/admin/shop/extGetImage.php";


		$.ajax({
			type: "POST",
			url: url ,
			data: { tmg_tp:tmg_tp, imageData:g_image_data, g_image_url : g_image_url},
			success: function(msg){

//caf2
//document.write(msg); 

				//if(msg == "ok") 

				window.close();
				return;

			},
		   error: function(request,status,error){


				window.close();
				return;

		   }
		 });
	 });


}


//이미지 array로 여러개 이미지 보내기, 현재 사용X
var aidx=0;
var im;
function getImage_next() {

	im = g_image_set[aidx];

	if(!im || typeof im === "undefined") { gethtml(); return false; }

	chrome.storage.local.get({'site_url':'','site_key':'','onoff':'','tab_url':'', 'site_config':''}, function(result) {
		site_url = result.site_url;
		site_key = result.site_key;

		site_url = mango_site_url(site_url);


		toDataUrl(im, function(myBase64) {

		var url = site_url+"mall/admin/shop/extGetImage.php";

			$.ajax({
				type: "POST",
				url: url ,
				data: { tmg_tp:tmg_tp, imageData:myBase64, index:aidx, g_image_url : im},
				success: function(msg){


					aidx++;
					getImage_next();

				},
			   error: function(request,status,error){


			   }
			 });
			
		});

	});

}



function get_onload() {
	

	var html = smode+'_'+tmg_tp;
	
	//g_onload_sleep 가 있으면 현재소스로 변경함.
	if(g_onload_sleep>0) html_source = document.documentElement.outerHTML;

	if(html_source) DOMtoString(html_source);

//	chrome.storage.local.get({'site_url':'','site_key':'','tab_url':'', 'site_config':'', [html]:''}, function(result) {

//		if(result[html]) DOMtoString(result[html]);
		
		chrome.storage.local.remove([html], function(){
		});
		// chrome.storage.local.set({[html]: ''});

		chrome.storage.local.remove([g_pop_name], function(){
		});
		// chrome.storage.local.set({[g_pop_name]: ''});


//	});

}


function DOMtoString(document_root) {

	var html = '',
	html = document_root;

//	var html_var = smode+'_'+tmg_tp;
//	chrome.storage.local.remove([html_var], function(){
//	});
//	chrome.storage.local.set({[html_var]: ''});

// alert(tab_url);

	var ret = '상품데이터 전송이 완료되었습니다.';

	site_url = mango_site_url(site_url);

	var url = site_url+"mall/admin/shop/extGoodsUpdate.php";
	var success_action;
	var fail_action;



	if(tab_url.indexOf("pmode=mango") != -1 ) {
		success_action = "getSource_Close";
		fail_action = "failSource_Close";
	} else {
		success_action = "getSource";
		fail_action = "failSource";
	}




	if(tab_url.indexOf("smode=search1") != -1 ) {
		smode = "search1";
	} else if(tab_url.indexOf("smode=search2") != -1 ) {
		smode = "search2";
	} else if(tab_url.indexOf("smode=detail") != -1 ) {
		smode = "detail";
	} else {
		smode = "";
	}


// 인코딩 삭제 22.6.22
//	html = encodeURI(html);
	
//	console.log("html : "+html);

	console.log("size : "+getByteLengthOfString(html) + " KB");


	const site_domain = new URL(site_url).hostname;

//console.log("site_domain : "+site_domain);
	
	var xx_clients = ["tmg1866.cafe24.com","tmg1859.cafe24.com","tmg1858.cafe24.com","tmg1800.cafe24.com","tmg1716.cafe24.com","tmg1442.cafe24.com","tmg1009.cafe24.com","tmg956.cafe24.com","tmg437.cafe24.com","tmg405.cafe24.com","tmg353.cafe24.com","tmg341.cafe24.com","tmg319.cafe24.com","tmg301.cafe24.com","tmg299.cafe24.com","tmg295.cafe24.com","tmg293.cafe24.com","tmg289.cafe24.com","tmg287.cafe24.com","tmg245.cafe24.com","tmg231.cafe24.com","tmg125.cafe24.com","tmg023.cafe24.com","tmg018.cafe24.com","tmg013.cafe24.com"];
	
	if (xx_clients.includes(site_domain)) {

// console.log("php5");

		$.ajax({
			type: "POST",
			url: url,
			data: {source:html, tab_url:tab_url, site_key:site_key, smode:smode, imageData:g_image_data, g_en_type:g_en_type,search2_end:search2_end},
			success: function(msg){
	 //caf2
	 // alert(msg);
	 //document.write(msg); 
	 //console.log("==> search2_end : "+search2_end);
	 //console.log("==> msg : "+msg);

				if(search2_end == 1 && smode=="search2" && msg.indexOf("setExtension_Search2") != -1) {
					
					gethtml();
					return;

				}


				if(msg == "setExtension_NoSite") {
					alert("고객님 서버에서 수집지원을 하지않는 사이트입니다");
					window.close();
					return;
				} else if(msg == "setExtension_NotUseSite") {
					alert("상품수집 및 업데이트가 제한된 사이트입니다.\n공지사항을 확인해주시기 바랍니다.");
					window.close();
					return;
				} else if(msg.indexOf("KEY_ERROR") != -1) {
					alert("서비스 인증 KEY가 잘못되었습니다.\n입력하신 서비스 인증 KEY를 다시한번 확인해보시기 바랍니다.");
					window.close();
					return;
				} else if(msg == "setExtension_Over") {
					alert("저장 가능한 상품수를 초과하였습니다.");
					window.close();
					return;
				} else if(msg == "setExtension_ErrorCoupangMyStore") {
					alert("쿠팡 내스토어 상품 수집 기능은 더망고에 등록된 쿠팡 아이디에 대한 스토어 상품만 수집할 수 있습니다.\n등록된 쿠팡 아이디에 대한 스토어 검색 URL을 입력하시거나\n[환경설정]-[마켓관리정보] 설정에서 쿠팡 아이디를 등록하신 후 수집하시기 바랍니다.");
					window.close();
					return;
				} else if(msg.indexOf("SearchPageError") != -1) {
					
					var alert_msg = msg.split("|");
					if(alert_msg[1]) alert(alert_msg[1]);
					else alert("본 페이지는 상품 수집이 가능한 URL 이 아닙니다.");
					window.close();
					return;

				} 


				if(g_debug == "Y")	{
				}
		
				var result = "";
				try{
					result = jQuery.parseJSON(msg.trim());
				} catch (e) {

				}


				if(result.mode == "buyb" || g_not_found == "Y") window.close();
				else if( ( tab_url.indexOf("urbanoutfitters.com") != -1 || tab_url.indexOf("tactics.com") != -1 || tab_url.indexOf("hapix.halfclub.com") != -1 || tab_url.indexOf("freepeople.com") != -1 || tab_url.indexOf("qogita.com") != -1 || tab_url.indexOf("bueromarkt-ag.de") != -1 || tab_url.indexOf("www.anthropologie.com") != -1 || tab_url.indexOf("choitemb2b.com") != -1) && g_direct_send != "Y") {
					setTimeout(function() {
						window.close(); //cafe24 계열
					}, 500);	
				}
				else {


					//페이지 직접 저장인 경우에만 alert 처리함.
					if(g_direct_send == "Y") {

						var error_code = result.error_code;
						var error_msg = result.error_msg;
						var limit_msg = result.limit_msg;


						var mode_msg = "";
						var goods_uid = result.goods_uid;
						if(goods_uid == null) goods_uid = "";


						if(result.mode == "insert") mode_msg = "( 신규저장 : 상품번호 "+goods_uid+" )";
						else if(result.mode == "update") mode_msg = "( 상품번호 "+goods_uid+" )";

						
						//상품번호 있고, 404 일 때만 정상
						if(error_code == "OK" || (mode_msg && error_code == "404")) {
							
							if(result.msg == "setExtension_Complete") {
								ret = "상품데이터 전송이 완료되었습니다.\n"+mode_msg;
							
							}

						}
						else {

							if(error_code == "limit") {
								if(error_msg) ret = "상품데이터 전송이 실패되었습니다.\n("+error_msg+")";
								else ret = "상품데이터 전송이 실패되었습니다.\n( 금지어 "+limit_msg+" 가 포함되어 있습니다. )";
							}
							else if(error_code == "limit_price") ret = "상품데이터 전송이 실패되었습니다.\n( 상품금액이 가격제한 설정 범위에 포함되지 않습니다. )"; 
							else if(error_code == "soldoutandnoreg") ret = "상품데이터 전송이 실패되었습니다.\n( 품절로 보여지는 상품으로 수집이 불가능한 상태입니다. )"; 
							else {
								if(error_msg) ret = "상품데이터 전송이 실패되었습니다.\n("+error_msg+")";
								else ret = "상품데이터 전송이 실패되었습니다.\n상품데이터 전송이 불가능한 상품페이지 또는 URL 입니다.";
							}
						}

						alert(ret);
						window.close();

					} 		
				}


			},
		   error: function(request,status,error){


		   }
		 });



	} else {
// console.log("php7+");
//console.log("==> g_extension_site_id : "+g_extension_site_id);
		const payload = {
			source: html,
			tab_url: tab_url,
			site_key: site_key,
			smode: smode,
			imageData: g_image_data,
			g_en_type: g_en_type,
			search2_end: search2_end,
			extension_site_id : g_extension_site_id
		};

		const gz = pako.gzip(JSON.stringify(payload));

		console.log("gzsize : " + (gz.length / 1024).toFixed(2) + " KB");

		$.ajax({
			type: "POST",
			url: url,
			// data: {source:html, tab_url:tab_url, site_key:site_key, smode:smode, imageData:g_image_data, g_en_type:g_en_type,search2_end:search2_end},
			data: gz,
			processData: false,
			contentType: "application/octet-stream",
			// headers: { "X-Content-Encoding": "gzip", "X-Payload-Type": "json" },		
			success: function(msg){
	//caf2
	// alert(msg);
	//document.write(msg); 
	//console.log("==> search2_end : "+search2_end);
	//console.log("==> msg : "+msg);



				if(search2_end == 1 && smode=="search2" && msg.indexOf("setExtension_Search2") != -1) {
					
					gethtml();
					return;

				}


				if(msg == "setExtension_NoSite") {
					alert("고객님 서버에서 수집지원을 하지않는 사이트입니다");
					window.close();
					return;
				} else if(msg == "setExtension_NotUseSite") {
					alert("상품수집 및 업데이트가 제한된 사이트입니다.\n공지사항을 확인해주시기 바랍니다.");
					window.close();
					return;
				} else if(msg.indexOf("KEY_ERROR") != -1) {
					alert("서비스 인증 KEY가 잘못되었습니다.\n입력하신 서비스 인증 KEY를 다시한번 확인해보시기 바랍니다.");
					window.close();
					return;
				} else if(msg == "setExtension_Over") {
					alert("저장 가능한 상품수를 초과하였습니다.");
					window.close();
					return;
				} else if(msg == "setExtension_ErrorCoupangMyStore") {
					alert("쿠팡 내스토어 상품 수집 기능은 더망고에 등록된 쿠팡 아이디에 대한 스토어 상품만 수집할 수 있습니다.\n등록된 쿠팡 아이디에 대한 스토어 검색 URL을 입력하시거나\n[환경설정]-[마켓관리정보] 설정에서 쿠팡 아이디를 등록하신 후 수집하시기 바랍니다.");
					window.close();
					return;
				} else if(msg.indexOf("SearchPageError") != -1) {
					
					var alert_msg = msg.split("|");
					if(alert_msg[1]) alert(alert_msg[1]);
					else alert("본 페이지는 상품 수집이 가능한 URL 이 아닙니다.");
					window.close();
					return;

				} 


				if(g_debug == "Y")	{
				}
		
				var result = "";
				try{
					result = jQuery.parseJSON(msg.trim());
				} catch (e) {

				}


				if(result.mode == "buyb" || g_not_found == "Y") window.close();
				else if( ( tab_url.indexOf("urbanoutfitters.com") != -1 || tab_url.indexOf("louisvuitton.com") != -1 || tab_url.indexOf("zara.com") != -1 || tab_url.indexOf("tactics.com") != -1 || tab_url.indexOf("hapix.halfclub.com") != -1 || tab_url.indexOf("freepeople.com") != -1 || tab_url.indexOf("qogita.com") != -1 || tab_url.indexOf("bueromarkt-ag.de") != -1 || tab_url.indexOf("www.anthropologie.com") != -1 || tab_url.indexOf("choitemb2b.com") != -1) && g_direct_send != "Y") {
					setTimeout(function() {
						window.close(); //cafe24 계열
					}, 500);	
				}
				else {


					//페이지 직접 저장인 경우에만 alert 처리함.
					if(g_direct_send == "Y") {

						var error_code = result.error_code;
						var error_msg = result.error_msg;
						var limit_msg = result.limit_msg;


						var mode_msg = "";
						var goods_uid = result.goods_uid;
						if(goods_uid == null) goods_uid = "";


						if(result.mode == "insert") mode_msg = "( 신규저장 : 상품번호 "+goods_uid+" )";
						else if(result.mode == "update") mode_msg = "( 상품번호 "+goods_uid+" )";

						
						//상품번호 있고, 404 일 때만 정상
						if(error_code == "OK" || (mode_msg && error_code == "404")) {
							
							if(result.msg == "setExtension_Complete") {
								ret = "상품데이터 전송이 완료되었습니다.\n"+mode_msg;
							
							}

						}
						else {

							if(error_code == "limit") {
								if(error_msg) ret = "상품데이터 전송이 실패되었습니다.\n("+error_msg+")";
								else ret = "상품데이터 전송이 실패되었습니다.\n( 금지어 "+limit_msg+" 가 포함되어 있습니다. )";
							}
							else if(error_code == "limit_price") ret = "상품데이터 전송이 실패되었습니다.\n( 상품금액이 가격제한 설정 범위에 포함되지 않습니다. )"; 
							else if(error_code == "soldoutandnoreg") ret = "상품데이터 전송이 실패되었습니다.\n( 품절로 보여지는 상품으로 수집이 불가능한 상태입니다. )"; 
							else {
								if(error_msg) ret = "상품데이터 전송이 실패되었습니다.\n("+error_msg+")";
								else ret = "상품데이터 전송이 실패되었습니다.\n상품데이터 전송이 불가능한 상품페이지 또는 URL 입니다.";
							}
						}

						alert(ret);
						window.close();

					} 		
				}


			},
		   error: function(request,status,error){


		   }
		 });
	 
	}



}



function send_msg(ret) {
	return ret;
}


const getByteLengthOfString = function(s,b,i,c){
    for(b=i=0;c=s.charCodeAt(i++);b+=c>>11?3:c>>7?2:1);
    return b/1000;
};				

//					var form = document.createElement("form");
//					var onekey = document.createElement("input");
//					var gmtCreate = document.createElement("input");
//					var checkCodeIds = document.createElement("input");
//					var secStrNoCCode = document.createElement("input");
//					var tb_token = document.createElement("input");
//					var item_url_refer = document.createElement("input");
//					var item_id = document.createElement("input");
//					var item_id_num = document.createElement("input");
//					var current_price = document.createElement("input");
//					var quantity = document.createElement("input");
//					var skuId = document.createElement("input");
//					var from = document.createElement("input");
//
//					form.method = "POST";
//					form.action = "https://buy.taobao.com/auction/buy_now.jhtml";
//					form.name = "themango_form";
//					//  form.id = "form_id";
//
//					onekey.type = "hidden";
//					onekey.name = "onekey";
//					onekey.value = "";
//
//					gmtCreate.type = "hidden";
//					gmtCreate.name = "gmtCreate";
//					gmtCreate.value = "";
//
//					checkCodeIds.type = "hidden";
//					checkCodeIds.name = "checkCodeIds";
//					checkCodeIds.value = "";
//
//					secStrNoCCode.type = "hidden";
//					secStrNoCCode.name = "secStrNoCCode";
//					secStrNoCCode.value = "";
//
//					tb_token.type = "hidden";
//					tb_token.name = "tb_token";
//					tb_token.value = "eb94e0170d363";
//
//					item_url_refer.type = "hidden";
//					item_url_refer.name = "item_url_refer";
//					item_url_refer.value = "https://s.taobao.com";
//
//					item_id.type = "hidden";
//					item_id.name = "item_id";
//					item_id.value = "652185119856";
//
//					item_id_num.type = "hidden";
//					item_id_num.name = "item_id_num";
//					item_id_num.value = "652185119856";
//
//					current_price.type = "hidden";
//					current_price.name = "current_price";
//					current_price.value = "5.00";
//
//					quantity.type = "hidden";
//					quantity.name = "quantity";
//					quantity.value = "1";
//
//					skuId.type = "hidden";
//					skuId.name = "skuId";
//					skuId.value = "4875273107729";
//
//					from.type = "hidden";
//					from.name = "from";
//					from.value = "item_detail";
//
//
//				  form.appendChild(onekey);
//				  form.appendChild(gmtCreate);
//				  form.appendChild(checkCodeIds);
//				  form.appendChild(secStrNoCCode);
//				  form.appendChild(tb_token);
//				  form.appendChild(item_url_refer);
//				  form.appendChild(item_id);
//				  form.appendChild(item_id_num);
//				  form.appendChild(quantity);
//				  form.appendChild(skuId);
//				  form.appendChild(from);
//
//				  document.body.appendChild(form);

//				  form.submit();


//alert 출력
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

    if (request.action === "showAlert") {
        alert(request.message);
    }
});


document.addEventListener("click", async (e) => {
	const img = e.target.closest("img.cs_goods_image");
	if (!img) return;

	const imageUrl = img.src;

	// 이미지 URL을 background로 전달
	chrome.runtime.sendMessage({
	  type: "taobao_image_search",
	  imageUrl: imageUrl
	});
});

// 관리자 페이지에서 확장프로그램 자동세팅 메시지 수신
window.addEventListener("message", function(e) {
	if (e.source !== window) return;
	if (!e.data || e.data.type !== "MANGO_AUTO_SETUP") return;
	chrome.storage.local.set({site_url: e.data.url, site_key: e.data.key}, function() {
		chrome.storage.sync.set({site_url_sync: e.data.url, site_key_sync: e.data.key});
		window.postMessage({type: "MANGO_AUTO_SETUP_DONE"}, "*");
	});
  });