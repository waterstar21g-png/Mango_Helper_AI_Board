function toDataUrl(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function() {
        var reader = new FileReader();
        reader.onloadend = function() {
            callback(reader.result);
        }
        reader.readAsDataURL(xhr.response);
    };
    xhr.open('GET', url);
    xhr.responseType = 'blob';
    xhr.send();
}


function getBase64Image(img) {
  var canvas = document.createElement("canvas");
  canvas.width = img.width;
  canvas.height = img.height;
  var ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);
  var dataURL = canvas.toDataURL("image/png");
  return dataURL.replace(/^data:image\/(png|jpg);base64,/, "");
}



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
//	else if(url.indexOf("eastbay.com") != -1 && url.indexOf("smode=search") != -1 && url.indexOf("query=") != -1) { 
//
//		var result = url.split("#");
//		var result2 = result[1].split(":");
//		
//		result.forEach(function(value){
//
//			if(value.indexOf("pmode=") != -1) params['pmode'] = value.replace("pmode=", "");
//			if(value.indexOf("smode=") != -1) params['smode'] = value.replace("smode=", "");
//			if(value.indexOf("tmg_tp=") != -1) params['tmg_tp'] = value.replace("tmg_tp=", "");
//			//if(value.indexOf("tmg_cnt=") != -1) params['tmg_cnt'] = value.replace("tmg_cnt=", "");
//
//		});
//
//
//
//	} 
	else {

		url.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str, key, value) { params[key] = value; });
	}
	return params;
}

function updateUrlParameter(url, key, value) {
    var regex = new RegExp(`([?&])${key}=.*?(&|$)`, "i");
    var separator = url.indexOf('?') !== -1 ? "&" : "?";
    if (url.match(regex)) {
        return url.replace(regex, `$1${key}=${value}$2`);
    } else {
        return url + separator + key + "=" + value;
    }
}

function sendTheMango(url) {
	
	var ext_url = url + "&pmode=mango&smode=detail&tmg_tp=D1234567";
	pop_extension = window.open(ext_url, "mango_pop","width=800,height=700,toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=no");
}




//function getBase64Image(img) {
//
//        // Create an empty canvas element
//
//        var canvas = document.createElement("canvas");
//
//        canvas.width = img.width;
//
//        canvas.height = img.height;
//
//        // Copy the image contents to the canvas
//
//        var ctx = canvas.getContext("2d");
//
//        ctx.drawImage(img, 0, 0);
//
//
//
//        // Get the data-URL formatted image
//
//        // Firefox supports PNG and JPEG. You could check img.src to
//
//        // guess the original format, but be aware the using "image/jpg"
//
//        // will re-encode the image.
//
//        var dataURL = canvas.toDataURL("image/png");
//
//        return dataURL.replace(/^data:image\/(png|jpg);base64,/, "");
//
//}



function setCookie(cookie_name, value, days, domain) {
  var exdate = new Date();
  exdate.setDate(exdate.getDate() + days);
  // 설정 일수만큼 현재시간에 만료값으로 지정

  var cookie_value = escape(value) + ((days == null) ? '' : ';    expires=' + exdate.toUTCString());
  if (domain) cookie_value += '; path=/; domain=' + domain;
  document.cookie = cookie_name + '=' + cookie_value;
}

var deleteCookie = function(name) {
document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
}

function deleteCookieDomain(name, domain) {
	document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=' + domain;
}

function chk_config_site(array_site_config, tab_url) {
	
	var domain="";
	var sp1 = tab_url.split("://");
	var sp2;
	if(sp1[1].indexOf("/") != -1) {
		sp2 = sp1[1].split("/");
		domain = sp2[0];
	} else if(sp1[1].indexOf("?") != -1) {
		sp2 = sp1[1].split("?");
		domain = sp2[0];
	} else {
		domain = tab_url;
	}


	var ret = false;
	for(var i=0; i < array_site_config.length; i++) {
		if(domain.indexOf(array_site_config[i]) != -1 ) {
			ret = true;
			break;
		}
	}

	return ret;

}

function mango_site_url(site_url) {

	if(site_url.indexOf("http://") != -1) {
		site_url = site_url.replace("http://", "https://");
	}

	var lastChar = site_url.substr(site_url.length - 1);
	if(lastChar != "/") site_url += "/";

	return site_url;


}


function fnv1aHash(str) {
    let hash = 2166136261; // FNV offset basis
    for (let i = 0; i < str.length; i++) {
        hash ^= str.charCodeAt(i); // XOR with the byte value
        hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24); // FNV prime multiplication
    }
    return hash >>> 0; // Return as an unsigned 32-bit integer
}

// 일정한 랜덤 숫자 생성 함수
function getConsistentRandomNumber(str, min, max) {
    const hashValue = fnv1aHash(str);
    // 범위 내로 해시 값을 매핑
    const range = max - min + 1;
    const randomNumber = (hashValue % range) + min;
    return randomNumber;
}


async function cleanupExpiredCtxKeys() {
	const all = await chrome.storage.local.get(null);
	const now = Date.now();

	for (const [key, payload] of Object.entries(all)) {
	  if (key.startsWith("ctx:")) {
		
		const expiresAt = payload?.expiresAt;
		if (!expiresAt || now > expiresAt) {
		  chrome.storage.local.remove(key);
		  console.log("🧹 삭제된 키:", key);
		}
	  }
	}
  }
