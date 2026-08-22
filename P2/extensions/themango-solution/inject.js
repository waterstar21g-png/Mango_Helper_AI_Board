
var mango_refer = window.location.href;
var now_url = window.location.href;
var pop_name = window.name;
var refer = document.referrer; 
//alert(pop_name);
// alert(refer);

 
// chrome.runtime.sendMessage({ type: "GET_CONTEXT" }, (ctx) => {
	
// 	const winKey = `${ctx.windowId}`;
// 	const tabKey = `${ctx.tabId}`;

// 	var params = {};
// 	mango_refer.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str, key, value) { params[key] = value; });
// 	chrome.storage.local.set({[pop_name]: params['url']});

	

// 	alert("winKey : "+winKey + ", tabKey : " + tabKey);
// });


function saveUrlToLocalStorage() {
	const params = new URLSearchParams(location.search);
	const urlParam = params.get("url");
  
	if (!urlParam) return; // url 파라미터가 없으면 저장 안 함
  
	const baseURL = decodeURIComponent(urlParam);
  
	// "url"과 "storage"는 제외하고 나머지 파라미터만 추출
	const { url, storage, ...otherParams } = Object.fromEntries(params.entries());
  
	const queryString = new URLSearchParams(otherParams).toString();
	const separator = baseURL.includes('?') ? '&' : '?';
  
	// const finalURL = queryString ? `${baseURL}${separator}${queryString}` : baseURL;
	const finalURL = queryString ? `${baseURL}${separator}${queryString}` : baseURL;

	const EXPIRATION_MS = 1 * 60 * 1000; 
	const payload = {
		finalURL: finalURL,
		expiresAt: Date.now() + EXPIRATION_MS
	};

	chrome.runtime.sendMessage({ type: "GET_CONTEXT" }, async (ctx) => {
	  const storageKey = `ctx:${ctx.windowId}_${ctx.tabId}`;
	  chrome.storage.local.set({ [storageKey]: payload });
	//   console.log("저장된 finalURL:", finalURL);
	});
}
  
if (mango_refer.includes("extGoodsPop.php")) {
	saveUrlToLocalStorage();
}
   
var cookies = document.cookie;
 
if(pop_name.indexOf("minettiangeloonline") != -1) {
	
	//ASPSESSIONIDSCQDTRBD,ASPSESSIONIDSARCRTAD 형태의 쿠키값이 계속 변경됨.

	var session_cookie;
	var session_key;
	var session_value;

	var sp = cookies.split(";");
	for(var i=0;i<sp.length;i++) {

		if(sp[i].indexOf("ASPSESSION") != -1) {
			
			session_cookie = sp[i].trim();
			if(session_cookie.indexOf("=") != -1) {

				var sp2 = session_cookie.split("=");
				session_key = sp2[0].trim();
				session_value = sp2[1].trim();
				
				if(session_value) {
					setCookie(session_key,session_value,5);
				}
			}

		}
	}
}

//else if(pop_name.indexOf("taobao") != -1) {
//
//	if(now_url.indexOf("tmall.com/item.htm") != -1) {
//
//		if(now_url.indexOf("tmg=y") != -1) {}
//		else {
//			chrome.storage.local.get({'site_url':'','site_key':'','onoff':'','tab_url':'', 'site_config':''}, function(result) {
//				site_url = result.site_url;
//				site_key = result.site_key;
//				
//				if(site_url) {
//					site_url = mango_site_url(site_url);
//					var sibUrl2 = site_url+"/mall/admin/taobao.js";
//					$.getScript(sibUrl2, function(data, textStatus, jqxhr) {
//						//	console.log(textStatus); 
//						//	console.log(jqxhr.status); 
//					});
//
//				}
//			});
//		}
//	}
//}



//if(now_url.indexOf("pmode=mango") != -1 && now_url.indexOf("detail.tmall.com/item.htm") != -1) {
//	
////	var param = getUrlParams(now_url);
////
////	if(now_url.indexOf("&tm_redirect=")  != -1 ) {
////		
////		var tm_redirect = param.tm_redirect;
////		tm_redirect = parseInt(tm_redirect)
////		
////		if(tm_redirect>3) {}
////		else {
////
////			var n_tm_redirect = 0;
////			n_tm_redirect = tm_redirect + 1;
////		
////			now_url = now_url.replace("item.htm", "item_o.htm");
////			now_url = now_url.replace("&tm_redirect="+tm_redirect, "&tm_redirect="+n_tm_redirect);
////			location.replace(now_url);
////		}
////
////
////	}
////	else {
////		now_url = now_url.replace("item.htm", "item_o.htm");
////		now_url = now_url+"&tm_redirect=1";
////		location.replace(now_url);
////	}
//
//}

//alert(pop_name);

if(pop_name.indexOf("open_extension") != -1 && pop_name.indexOf("|") != -1) {
	var pop_exp = pop_name.split("|");
	pop_name = pop_exp[0];
}


if(pop_name.indexOf("open_extension") != -1 && pop_name.indexOf("?") != -1) {
	var ppp = pop_name.match( /open\_extension(.*?)\?/si  );
	pop_name = "open_extension"+ppp[1];
}

if (mango_refer.indexOf("extGoodsPop.php") != -1 && mango_refer.indexOf("storage=1") != -1) { 
	
	var params = {};
	mango_refer.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str, key, value) { params[key] = value; });
	// chrome.storage.local.set({[pop_name]: params['url']});

	if(mango_refer.indexOf("sivillage.com") != -1) sleep(3000); //스토리지 저장시간동안 잠시 대기


} else if (mango_refer.indexOf("extGoodsPop.php") != -1 && mango_refer.indexOf("storage=2") != -1) { 
	
	var params = {};
	mango_refer.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str, key, value) { params[key] = value; });
	
	const baseURL = decodeURIComponent(params['url']);
	const { url, storage, ...otherParams } = params;
	const queryString = new URLSearchParams(otherParams).toString();
	const separator = baseURL.includes('?') ? '&' : '?';
	
	const finalURL = `${baseURL}${separator}${queryString}`;
	// alert("finalURL : "+finalURL);

	// chrome.storage.local.set({[pop_name]: finalURL});

} 
else {
	// alert(now_url);
	if(now_url.indexOf("halfclub.com")){}
	else chrome.storage.local.remove([pop_name]);
 
	// chrome.storage.local.set({[pop_name]: ''});

}

/*
if(now_url.indexOf("balaan.co.kr/products") != -1 ) {

	 function override_alert() {
		window.alert = function alert(msg) {
			console.log('Hidden Alert ' + msg);
		};
	}


	 if (!document.xmlVersion) {
			var script = document.createElement('script');
			script.appendChild(document.createTextNode('(' + override_alert + ')();'));
			document.documentElement.appendChild(script);
	 }


	window.opener = null;
}

else if(now_url.indexOf("wemakeprice.com/product") != -1 ) {

	if (mango_refer.indexOf("extGoodsPop.php") != -1 || mango_refer.indexOf("pmode=mango") != -1) {
		
		 function override_alert() {
			window.alert = function alert(msg) {
				console.log('Hidden Alert ' + msg);
			};
		}

		 function override_close() {
			window.close = function alert(msg) {
				console.log('Window Close ' + msg);
			};
		}

		 if (!document.xmlVersion) {
				var script = document.createElement('script');
				script.appendChild(document.createTextNode('(' + override_alert + ')();'));
				script.appendChild(document.createTextNode('(' + override_close + ')();'));
				document.documentElement.appendChild(script);

		 }

	}

}


else if(now_url.indexOf("ssg.com/item/itemView.ssg") != -1 || mango_refer.indexOf("folderstyle.com/shop/goodsView/") != -1) {

	//alert 삭제
	 function override_alert() {
		window.alert = function alert(msg) {
			console.log('Hidden Alert ' + msg);
		};
	}

	 function override_confirm() {
		window.confirm = function alert(msg) {
			console.log('Window Confirm ' + msg);
		};
	}


	 if (!document.xmlVersion) {
			var script = document.createElement('script');
			script.appendChild(document.createTextNode('(' + override_alert + ')();'));
			script.appendChild(document.createTextNode('(' + override_confirm + ')();'));
			document.documentElement.appendChild(script);
	 }

}

else if( now_url.indexOf("shop.ihanstyle.com/product.do") != -1 || now_url.indexOf("nppip.com/shop/item.php") != -1 || now_url.indexOf("sellingkok.com/shop/item.php") != -1 || now_url.indexOf("halfclub.com/#!/product") != -1 || now_url.indexOf("halfclub.com/product") != -1 || now_url.indexOf("sneakermania.co.kr/goods/goods_view.php") != -1 || now_url.indexOf("elandmall.co.kr/i/item") != -1 || now_url.indexOf("ople.com/mall5/shop/item.php") != -1 || now_url.indexOf("musinsa.com/app/goods") != -1 || now_url.indexOf("imarket.co.kr/product/") != -1 || now_url.indexOf("wconcept.co.kr/Product/") != -1 || now_url.indexOf("hellosoccer.co.kr/shop/shopdetail.html") != -1 || now_url.indexOf("bananab2b.co.kr") != -1 || now_url.indexOf("hoyaamall.co.kr") != -1 || now_url.indexOf("wholesaledepot.co.kr/shop/goods/goods_view.php") != -1 || now_url.indexOf("hoyaamall.co.kr") != -1 || mango_refer.indexOf("jentestore.com") != -1 || mango_refer.indexOf("atmos-seoul.com") != -1 || mango_refer.indexOf("lfmall.co.kr/product.do") != -1 || mango_refer.indexOf("//display.cjonstyle.com") != -1 || mango_refer.indexOf("mustit.co.kr") != -1 || mango_refer.indexOf("//www.g9.co.kr") != -1 || mango_refer.indexOf("ssg.com/item/itemView.ssg") != -1 || mango_refer.indexOf("//item.gmarket.co.kr") != -1 || now_url.indexOf("item.gmarket.co.kr") != -1 || mango_refer.indexOf("11st.co.kr/product") != -1 || mango_refer.indexOf("nbkorea.com/product/productDetail.action") != -1 || mango_refer.indexOf("styledome.net/shop/item.php") != -1 || mango_refer.indexOf("a-rt.com/product") != -1 || mango_refer.indexOf("shoemarker.co.kr/ASP/Product/ProductDetail.asp") != -1 ) {


	if (mango_refer.indexOf("extGoodsPop.php") != -1 || mango_refer.indexOf("pmode=mango") != -1) {

		//alert 삭제
		 function override_alert() {
			window.alert = function alert(msg) {
				console.log('Hidden Alert ' + msg);
			};
		}

		 if (!document.xmlVersion) {

			var script = document.createElement('script');
			script.appendChild(document.createTextNode('(' + override_alert + ')();'));
			document.documentElement.appendChild(script);
		 }




	}
}
*/


function getUrlParams(url) {

	var params = {};

	if(url.indexOf("maxaroma.com") != -1 && url.indexOf("smode=search") != -1) { 
	
		var result = url.split('/');
		result.forEach(function(value){

			if(value.indexOf("pmode=") != -1) params['pmode'] = value.replace("pmode=", "");
			if(value.indexOf("smode=") != -1) params['smode'] = value.replace("smode=", "");
			if(value.indexOf("tmg_tp=") != -1) params['tmg_tp'] = value.replace("tmg_tp=", "");
			if(value.indexOf("tmg_sruid=") != -1) params['tmg_sruid'] = value.replace("tmg_sruid=", "");
			//if(value.indexOf("tmg_cnt=") != -1) params['tmg_cnt'] = value.replace("tmg_cnt=", "");

		});

	} 

	else {

		url.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str, key, value) { params[key] = value; });
	}
	return params;
}



function sleep(ms) {
  const wakeUpTime = Date.now() + ms;
  while (Date.now() < wakeUpTime) {}
}


function setCookie(cookie_name, value, days, domain) {
  var exdate = new Date();
  exdate.setDate(exdate.getDate() + days);
  // 설정 일수만큼 현재시간에 만료값으로 지정

  var cookie_value = escape(value) + ((days == null) ? '' : ';    expires=' + exdate.toUTCString());
  if (domain) cookie_value += '; path=/; domain=' + domain;
  document.cookie = cookie_name + '=' + cookie_value;
}


function getCookie(cookieName){
    var cookieValue=null;
    if(document.cookie){
        var array=document.cookie.split((escape(cookieName)+'='));
        if(array.length >= 2){
            var arraySub=array[1].split(';');
            cookieValue=unescape(arraySub[0]);
        }
    }
    return cookieValue;
}


//alert(document.documentElement.outerHTML);
//location.href="javascript: window.alert = function(x) {console.log(x)};"
//location.href="javascript: window.alert = function(x) {console.log(x)}; window.confirm = function(){return true;};";

