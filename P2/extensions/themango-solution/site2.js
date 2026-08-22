(() => {
 
	const origXHROpen = XMLHttpRequest.prototype.open;
	const now_url = window.location.href;

	
	XMLHttpRequest.prototype.open = function (method, url, ...rest) {

// console.log(`======> XHR option request: ${method} ${url}`);
		let is_intercept = false;
		let multiple_payload = false; //true 이면 모든 요청을 다 themango_payload에 담음
		let url_encode = true;
		let site_type = "";

		if(typeof url === "string") {
			
			if( now_url.includes("brand.naver.com") || now_url.includes("smartstore.naver.com") ) {

				if( url.includes("/products/") && url.includes("?withWindow=false") ) {	// brand.naver.com + smartstore.naver.com
					is_intercept = true;
				} 
			}

			else if( now_url.includes("decathlon.co.kr")) {

				if( url.includes("/api/fulfiller/itemAvailability") ) { //상세
					site_type = 1;
					is_intercept = true;
				}
				
				else if( url.toLowerCase().includes("wb3tmfnsaz-dsn.algolia.net/1/indexes/prod_pim_v1_index/query") ) { //검색
					site_type = 2;
					is_intercept = true;
					multiple_payload = true;
					url_encode = false;
				}
			}
		}

		if( is_intercept ) {
			//console.log(`XHR option request: ${method} ${url}`);

			this.addEventListener("load", function () {
				try {
//console.log("XHR 상태 코드:", this.status, this.readyState);
// console.log("XHR 응답 텍스트 길이:", resText.length);
// console.log("==> resText:", resText);
					
					let resText = this.responseText;
					resText = handleResText(now_url, url, resText, site_type, url_encode);

					if (resText) {

						if(!multiple_payload) {

							const div = document.createElement('div');
							div.className = 'themango_payload';
							div.style.display = 'none';
							div.textContent = resText; 
							document.documentElement.appendChild(div);
						}
						else {

							// 기존 payload 개수 확인
							const existing = document.querySelectorAll('[class^="themango_payload"]');
							const nextIndex = existing.length + 1;
			
							const div = document.createElement('div');
							div.className = 'themango_payload' + nextIndex; // 단일 클래스
							div.style.display = 'none';
							div.textContent = resText;

							document.documentElement.appendChild(div);
						}

					} else {
						//console.warn("XHR 응답이 JSON 형태가 아님 또는 빈 응답");
					}
				} catch (e) {
					//console.error("XHR 응답 처리 실패:", e);
				}
			});
		}

		return origXHROpen.apply(this, [method, url, ...rest]);
	};
	


	const origFetch = window.fetch;
	window.fetch = function (input, init) {
	  let url = "";
  
	  if (typeof input === "string") {
		url = input;
	  } else if (input instanceof Request) {
		url = input.url;
	  }
  
	  let is_intercept = false;
 //console.log("==> now_url : "+now_url);
 //console.log("==> url : "+url);
 
	  if (typeof url === "string") {

		if (now_url.includes("kream.co.kr")) {
		  if (url.includes("api.kream.co.kr/api/p/options/display") && url.includes("picker_type=buy")) {
			is_intercept = true;
		  }
		} 
		else if( now_url.includes("injen.com")) {
			if( url.includes("api.sunhammer.io/products") ) { //검색
				is_intercept = true;
			}
		}
		else if( now_url.includes("shop.app")) {
			if( url.includes("/web/api/graphql") ) { 
				is_intercept = true;
			}
		}
	  }


	  // 원래 fetch 실행
	  const fetchPromise = origFetch.call(this, input, init);

	  if (!is_intercept) {
		return fetchPromise; // 평소처럼 리턴
	  }
  
	  return fetchPromise.then((res) => {
		try {
		  const clone = res.clone();
		  clone.text().then((text) => {
  
			const div = document.createElement('div');
			div.className = 'themango_payload';
			div.style.display = 'none';
			div.textContent = encodeURI(text);
			document.documentElement.appendChild(div);
		  }).catch((e) => {
			console.error("error :", e);
		  });
		} catch (e) {
		  console.error("error :", e);
		}
  
		return res; // 원래 응답은 그대로 페이지에 전달
	  });
	};




	// 타오바오가 기존 xhr 방식에서 script 방식으로 바꿈. script 일때도 처리하기 위함.
	// if (now_url.includes("taobao.com") || now_url.includes("tmall.com")) {
	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {

			for (const node of mutation.addedNodes) {

				let is_script = false;
				let tagname = "";
				if (node.tagName) {
					tagname = node.tagName.toLowerCase();
				}

				if (now_url.includes("taobao.com") || now_url.includes("tmall.com") ) {
					// console.log('result => ' + node.src);
					
					if (tagname === "script" && node.src.includes("mtop.taobao.pcdetail.data.get")) is_script = true;
				}
				else if (now_url.includes("aliexpress.com")) {
					if (tagname === "script" && node.src.includes("acs.aliexpress.com/h5/mtop.aliexpress.pdp.pc.query")) is_script = true;
					// if (tagname === "script" && node.src.includes("acs.aliexpress.com/h5/mtop.ae.shop.search.product.group")) is_script = true;
				}
				else if (now_url.includes("timeshop24.com")) {
					if (tagname === "script" && node.type.includes("x-magento-init")) {
						// console.log(node);
						const text = node.textContent;

						const hasGalleryPlaceholder = text.includes('data-gallery-role=gallery-placeholder');
						const hasMagnify = text.includes('magnifier/magnify');
						
						if (hasGalleryPlaceholder && hasMagnify) {
							appendThemangoPayload(text);
						}
						// is_script = true;
					}
				}
				
				if(is_script) {

					// 페이지 context에서 직접 요청 → 브라우저가 자동으로 쿠키, 토큰 붙여줌
					fetch(node.src, { credentials: "include" })
					.then(res => res.text())
					.then(text => {

						const div = document.createElement('div');
						div.className = 'themango_payload';
						div.style.display = 'none';
						div.textContent = encodeURI(text);
						document.documentElement.appendChild(div);
					})
					.catch(err => console.error("요청 실패:", err));
				}
			}
		}
	});

	observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src"] });
	// }

	
	function appendThemangoPayload(text) {
		const div = document.createElement('div');
		div.className = 'themango_payload';
		div.style.display = 'none';
		div.textContent = encodeURI(text);
		document.documentElement.appendChild(div);
	}

	function handleResText(now_url, data_url, resText, site_type, url_encode) {
		// console.log('data_url => ' + data_url);


		var returnData = resText;
		// console.log('now_url => ' + now_url);

		try {
			
			if (now_url.indexOf("decathlon.co.kr") != -1) {
//console.log('resText => ' + resText);
				
				if(site_type == 2) {  //검색

					var json = JSON.parse(resText);

					// hits 만 존재하면 그것만 반환, 없으면 빈 배열
					if (json.hasOwnProperty("hits")) {

						// hits만 남기고 반환할 JSON 구성
						var filtered = {
							hits: json.hits
						};

						returnData = JSON.stringify(filtered);

					} else {
						// hits 없으면 빈 구조라도 반환
						returnData = JSON.stringify({ hits: [] });
					}
				}

			}
		}
		catch(e) {
			// console.log("JSON 파싱 실패:", e);
			// 파싱 실패 시 원본 resText 그대로 반환
		}
		

		if(url_encode) returnData = encodeURI(returnData);
		return returnData;
		
	}




	
	// beseller.net :  더보기로 다음 상품이 나오는데. 더보기 클릭이 보안으로 다 막힘. 이 방법 밖에 없었음. 2026.4.25
	// neweracapkorea.com 도 같은 구조. 메이크샵 인 경우에 같은 현상임.
	if (now_url.includes("beseller.net") || now_url.includes("neweracapkorea.com")) {
		window.addEventListener('message', function(e) {
			if (e.source !== window) return;
			if (!e.data || e.data.source !== 'themango-ext') return;
			
			if (e.data.action === 'clickMoreBtn') {
				// is_last 체크 후 호출
				try {
					if (typeof MS_product !== 'undefined' && MS_product.data && MS_product.data().is_last === true) {
						// 마지막 페이지 - 호출하지 않음 (alert 방지)
						window.postMessage({ source: 'themango-ext-reply', action: 'isLast', value: true }, '*');
						return;
					}
				} catch(err) {}
				
				if (typeof get_more_product_list === 'function') {
					get_more_product_list();
				}
			}
		});
	}




})();


