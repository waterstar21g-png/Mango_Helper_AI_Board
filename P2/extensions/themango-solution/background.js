chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_CONTEXT") {
      if (sender.tab) {
        sendResponse({
          tabId: sender.tab.id,
          windowId: sender.tab.windowId,
        });
      } else {
        // (확장 페이지/사이드패널 등 sender.tab이 없는 경우 대비)
        chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
          const t = tabs[0];
          sendResponse({ tabId: t?.id, windowId: t?.windowId });
        });
      }
      return true; // async 응답
    }
});


// chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
//     if (request.action === "sendAjax") {
//         console.log("AJAX 요청 시작: ", request.data);

//         // fetch()를 사용하여 서버로 데이터 전송
//         fetch("https://scrap7.cafe24.com/mall/admin/shop/extGoodsUpdate.php", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/x-www-form-urlencoded",
//             },
//             body: new URLSearchParams({
//                 source: request.data.source
//             })
//         })
//         .then(response => response.json())
//         .then(data => {
//             console.log("✅ 서버 응답: ", data);
//             sendResponse({ success: true, response: data });
//         })
//         .catch(error => {
            
//         });

//         return true; // 비동기 응답을 보장
//     }
// });
 

chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
    if (message.type === "taobao_image_search") {
      const imageUrl = message.imageUrl;
  
      try {
        const blob = await fetch(imageUrl).then(res => res.blob());
        const formData = new FormData();
        formData.append("imgfile", blob, "upload.jpg");
  
        const res = await fetch("https://s.taobao.com/image", {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "include",
          redirect: "follow" // 자동 리디렉션
        });
  
        const text = await res.text();
        if (!text.startsWith("{")) {
          console.error("응답이 JSON이 아닙니다:", text);
          return;
        }
  
        const json = JSON.parse(text);
        const tfsid = json.name;
  
        if (!tfsid) {
          console.error("타오바오 업로드 실패:", json);
          return;
        }
  
        const today = new Date();
        const yyyymmdd = today.toISOString().split("T")[0].replace(/-/g, "");
        const searchUrl = `https://s.taobao.com/search?q=&tfsid=${encodeURIComponent(
          tfsid
        )}&app=imgsearch&js=1&ie=utf8&initiative_id=staobaoz_${yyyymmdd}`;
  
        chrome.tabs.create({ url: searchUrl });
      } catch (err) {
        console.error("에러 발생:", err);
      }
    }
  });
  


chrome.runtime.onInstalled.addListener(() => {
    console.log("Extension Installed and Running (Manifest V3)");
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message === "checkPopups") {
        chrome.contentSettings.popups.get({ primaryUrl: sender.tab.url }, (details) => {
            // console.log(details.setting);

            if (details.setting === "allow") {
                // console.log("팝업이 허용되어 있습니다.");
            } else {
                // console.warn("팝업이 허용되지 않았습니다.");
                
                // 현재 활성화된 탭에 메시지 전송
                chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                    if (tabs.length > 0) {
                        chrome.tabs.sendMessage(tabs[0].id, { action: "showAlert", message: "팝업이 허용되지 않았습니다.\n[환경설정] - [익스텐션 설치 메뉴얼]을 참고하여 팝업을 허용하신 후 이용하시기 바랍니다." });
                    }
                });
            }
        });

        return true;
    }
});



chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete") {
        let url = changeInfo.url || tab.url;

        // console.log("탭 업데이트 감지됨:", url);

        if (url.includes("pmode=mango")) {
            if (url.includes("footpop.co.kr") || url.includes("beseller.net")) {
                fetch(url)
                    .then(response => {
                        if (response.status === 404) {
                            chrome.storage.local.get({ site_url: "", site_key: "" }, (result) => {
                                let site_url = result.site_url;
                                let site_key = result.site_key;

                                send_404(site_url, site_key, url);
                            });
                        }
                    })
                    .catch(error => {
                        console.error("HTTP 요청 중 오류 발생:", error);
                    });
            }
        }
    }
});

function send_404(site_url, site_key, tab_url) {
    site_url = mango_site_url(site_url);
    let url = site_url + "mall/admin/shop/extGoodsUpdate.php";

    let param = getUrlParams(tab_url);
    let tmg_tp = param.tmg_tp;
    let smode = param.smode;
    let tmg_guid = param.tmg_guid;
    let direct_send = "";

    if (tab_url.includes("tmg_tp=D")) direct_send = "Y";

    if (tab_url.includes("footpop.co.kr")) {
        tab_url = `https://footpop.co.kr/not_found.html?pmode=mango&smode=detail&tmg_tp=${tmg_tp}&tmg_guid=${tmg_guid}`;
    } else if (tab_url.includes("beseller.net")) {
        tab_url = `https://beseller.net/not_found.html?pmode=mango&smode=detail&tmg_tp=${tmg_tp}&tmg_guid=${tmg_guid}`;
    }

    if (tab_url.includes("/not_found.html")) {
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
                source: "",
                tab_url: tab_url,
                site_key: site_key,
                smode: smode,
            }),
        })
            .then(response => response.text())
            .then(msg => {
                let result = {};
                try {
                    result = JSON.parse(msg.trim());
                } catch (e) {
                    console.error("JSON 파싱 오류:", e);
                }

                if (direct_send === "Y" && result.msg === "setExtension_Complete") {
                    console.log("해당 사이트에서 삭제된 상품으로 품절처리되었습니다.");
                }
            })
            .catch(error => console.error("AJAX 요청 오류:", error));
    }
}