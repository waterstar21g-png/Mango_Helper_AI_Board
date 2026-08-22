const w_pop_name = window.name;
const w_tab_url = window.location.href;
const w_mango_refer = document.referrer;

//console.log("==> w_pop_name : "+w_pop_name);

 if(w_pop_name.indexOf("open_extension") != -1 || w_tab_url.indexOf("pmode=mango") != -1 || w_mango_refer.indexOf("pmode%3Dmango") != -1 || w_mango_refer.indexOf("pmode=mango") != -1 ) {

//console.log("==> [site2] w_pop_name : "+w_pop_name);

	const script = document.createElement("script");
	script.src = chrome.runtime.getURL("site2.js");
	// (document.head || document.documentElement).appendChild(script);

	document.documentElement.appendChild(script);

	script.remove();



// 	window.addEventListener("message", (event) => {
// //console.log("==> type : "+event.data.type);
// 	  if (!event.data || event.data.type !== "DATA_INTERCEPTED") return;
// 	  const response = event.data.payload;
//  //console.log("🎯 옵션 응답 수신됨:", response);
//  	const json_response = JSON.stringify(response);
// 	 $('html').append('<div id="themango" style="display:none">'+json_response+'</div>');


	  // 여러창에서 동시에 진행하면, 스토리지 이름이 같아서 다른 창의 상품정보를 가져오는 경우가 있음.
	  // 스토리지 이름에 url 에서 추출한 상품번호를 추가함.
	  // site.js 에서 get 할때도 상품번호 키로 찾음.
	  // site.js 에서 .append 한 다음에 스토리지는 제거함. 메모리 문제 해결.
     
// 	 const prod_url = window.location.href;
// //console.log("==> prod_url : "+prod_url);
// 	let prodID = "";
// 	let storage_hd = "";
// 	 if (prod_url.includes("naver.com")) {
// 		 storage_hd = "NAVER_OPTION_DATA";
// 		 const parts = prod_url.split("/").filter(Boolean);
// 		 prodID = parts[parts.length - 1];
// 		 prodID = prodID.split("?")[0];

// 	 } else if (prod_url.includes("taobao.com")) {
// 		storage_hd = "TAOBAO_OPTION_DATA";
// 		const params = new URLSearchParams(new URL(prod_url).search);
// 		prodID = params.get("id");

// 	 }

//console.log("==> @@  prodID : "+prodID);

	//   chrome.storage.local.set({[`${storage_hd}::${prodID}`]: response});
	  
	// });

 }
