const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data["event"] == "New Flow") {
        addUrl(data);
    } else if (data["event"] == "Replay Flow Response") {
        const flow = data["flow-name"];
        const replayResponse = data["replay-response"];
        const status = data["status"];

        const ref = storage.get(flow);
        ref["replayResponse"] = replayResponse;
        ref["status"] = status;
        ref["truePositive"] = status == "different responses" ? true : false;
        
        renderUrls();
        selectUrl(selectedUrl);
    }
};

function toggleModal() {
    // Send the original and replay input to the python websocket server
    const originalInput = document.getElementById("originalInput").value;
    const replayInput = document.getElementById("replayInput").value;
    socket.send(JSON.stringify({ event: "Original/Replay Inputs", originalInput: originalInput, replayInput: replayInput }));
    
    // Toggle the active class for the modal
    const modalElem = document.getElementById('initialInput');
    modalElem.classList.toggle('active');
}

function replayRequest(flow) {
    // TODO: change the UI to show that the request is being done
    console.log(`Replaying request ${flow}`);

    storage.get(flow).status = "replaying";

    // Re-render the sidebar menu and the responses to show ney blue-ish UI
    if (selectedSidebarMenu == "not-replayed") {
        renderNotReplayedUrls();
    }
    renderResponsesMenus(flow);

    socket.send(JSON.stringify({ event: "Replay Flow", flow: flow }));
}

const json = `{"city":{"code":"brasilia","name":"Bras\u00edlia"},"country":{"code":["a","b","c","D"],"name":"Brazil","pt":"Brasil","ptSlug":"brasil"},"extra":{"city_uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF","region_name":"Distrito Federal","region_news_path":"df/distrito-federal"},"ip":"100.80.14.130","latitude":-15.7798,"longitude":-47.9331,"semantic":{"city":"brasilia","region":"distrito-federal","state":"df","uri":"http://semantica.globo.com/base/Cidade_Brasilia_DF"},"state":{"code":"DF","name":"Federal District"}}`

function createJSONLine(key, value, depth) {
    const container = document.createElement('div');
    container.className = `json-line depth-${depth}`;
    
    container.innerHTML = `
        <span class="key truncate" title="${key}">${key}</span>
        <span class="value">${value}</span>
    `;

    return container;
}

function renderJSON(json, elem, depth) {
    for (const key in json) {
        // if (!Object.hasOwn(json, key)) continue;

        const value = json[key];
        if (typeof(value) === "string" || typeof(value) === "number") {
            elem.appendChild(createJSONLine(key, value, depth));
            // console.log(value, typeof(value));
        } else if (typeof(value) === "object") {
            elem.appendChild(createJSONLine(key, "", depth));
            renderJSON(value, elem, depth+1);
        }
    }
}

const storage = new Map();

// storage.set("flow-0", { url: "https://1.bb.com.br", method: "GET", status: "not replayed", originalRequest: "originalRequest-1", replayRequest: "replayRequest-1", originalResponse: "originalResponses-1", replayResponse: "", truePositive: false });
// storage.set("flow-1", { url: "https://2.bb.com.br", method: "GET", status: "same response", originalRequest: "originalRequest-2", replayRequest: "replayRequest-2", originalResponse: "originalResponses-2", replayResponse: "replayResponses-2", truePositive: false });
// storage.set("flow-2", { url: "https://3.bb.com.br", method: "GET", status: "different responses", originalRequest: "originalRequest-3", replayRequest: "replayRequest-3", originalResponse: "originalResponses-3", replayResponse: "replayResponses-3", truePositive: true });
// storage.set("flow-3", { url: "https://4.bb.com.br", method: "GET", status: "different responses", originalRequest: "originalRequest-3", replayRequest: "replayRequest-3", originalResponse: "originalResponses-3", replayResponse: "replayResponses-3", truePositive: true });
// storage.set("flow-4", { url: "https://5.bb.com.br", method: "GET", status: "not replayed", originalRequest: "originalRequest-1", replayRequest: "replayRequest-1", originalResponse: "originalResponses-1", replayResponse: "", truePositive: false });

let selectedUrl = "";
let selectedSidebarMenu = "not-replayed";
function selectNotReplayed() {
    selectedSidebarMenu = "not-replayed";

    // DOM Elements
    const notReplayedElem = document.getElementById("not-replayed");
    const sameResponseElem = document.getElementById("same-response");
    const differentResponsesElem = document.getElementById("different-responses");

    // Select the right urls
    notReplayedElem.classList.add("selected");
    sameResponseElem.classList.remove("selected");
    differentResponsesElem.classList.remove("selected");

    // Render the urls
    renderUrls();
}

function selectSameResponse() {
    selectedSidebarMenu = "same-response";

    // DOM Elements
    const notReplayedElem = document.getElementById("not-replayed");
    const sameResponseElem = document.getElementById("same-response");
    const differentResponsesElem = document.getElementById("different-responses");

    // Select the right urls
    notReplayedElem.classList.remove("selected");
    sameResponseElem.classList.add("selected");
    differentResponsesElem.classList.remove("selected");

    // Render the urls
    renderUrls();
}

function selectDifferentResponses() {
    selectedSidebarMenu = "different-responses";

    // DOM Elements
    const notReplayedElem = document.getElementById("not-replayed");
    const sameResponseElem = document.getElementById("same-response");
    const differentResponsesElem = document.getElementById("different-responses");

    // Select the right urls
    notReplayedElem.classList.remove("selected");
    sameResponseElem.classList.remove("selected");
    differentResponsesElem.classList.add("selected");

    // Render the urls
    renderUrls();
}
selectNotReplayed();

function renderUrls() {
    if (selectedSidebarMenu == "not-replayed") {
        renderNotReplayedUrls();
    } else if (selectedSidebarMenu == "same-response") {
        renderSameResponseUrls();
    } else if (selectedSidebarMenu == "different-responses") {
        renderDifferentResponsesUrls();
    }
}

function renderNotReplayedUrls() {
    const urlsElem = document.getElementById("urls");
    urlsElem.innerHTML = ""

    for (const [key, value] of storage) {
        if (value["status"] != "not replayed" && value["status"] != "replaying") {
            continue;
        }

        const containerElem = document.createElement('div');
        if (value["status"] == "not replayed") {
            containerElem.className = "url status-a";
        } else {
            containerElem.className = "url status-d";
        }
        containerElem.id = key;
        containerElem.setAttribute("onclick", `selectUrl('${key}')`);

        const url = value["url"];
        const method = value["method"];
        const cleanUrl = url.replace(/^https?:\/\//, '');

        // Inject the inner HTML
        containerElem.innerHTML = `
            <span class="rapid-replay-button" onclick=replayRequest('${key}')>Repetir</span>
            <input type="checkbox" class="true-positive-check" disabled>
            <span class="http-verb http-${method.toLowerCase()}">${method}</span>
            <span class="url-text truncate" title="${url}">${cleanUrl}</span>
        `;

        urlsElem.appendChild(containerElem);

        if (selectedUrl == key) {
            selectUrl(selectedUrl);
        }
    }
}

function renderSameResponseUrls() {
    const urlsElem = document.getElementById("urls");
    urlsElem.innerHTML = ""

    for (const [key, value] of storage) {
        if (value["status"] != "same response") {
            continue;
        }

        const containerElem = document.createElement('div');
        containerElem.className = "url status-b";
        containerElem.id = key;
        containerElem.setAttribute("onclick", `selectUrl('${key}')`);

        const url = value["url"];
        const method = value["method"];
        const truePositive = value["truePositive"]
        const cleanUrl = url.replace(/^https?:\/\//, '');

        // Inject the inner HTML
        containerElem.innerHTML = `
            <input type="checkbox" class="true-positive-check" ${truePositive ? "checked" : ""} onclick="toggleFalsePositive('${key}')">
            <span class="http-verb http-${method.toLowerCase()}">${method}</span>
            <span class="url-text truncate" title="${url}">${cleanUrl}</span>
        `;

        urlsElem.appendChild(containerElem);

        if (selectedUrl == key) {
            selectUrl(selectedUrl);
        }
    }
}

function renderDifferentResponsesUrls() {
    const urlsElem = document.getElementById("urls");
    urlsElem.innerHTML = ""

    for (const [key, value] of storage) {
        if (value["status"] != "different responses") {
            continue;
        }

        const containerElem = document.createElement('div');
        containerElem.className = "url status-c";
        containerElem.id = key;
        containerElem.setAttribute("onclick", `selectUrl('${key}')`);

        const url = value["url"];
        const method = value["method"];
        const truePositive = value["truePositive"]
        const cleanUrl = url.replace(/^https?:\/\//, '');

        // Inject the inner HTML
        containerElem.innerHTML = `
            <input type="checkbox" class="true-positive-check" ${truePositive ? "checked" : ""} onclick="toggleFalsePositive('${key}')">
            <span class="http-verb http-${method.toLowerCase()}">${method}</span>
            <span class="url-text truncate" title="${url}">${cleanUrl}</span>
        `;

        urlsElem.appendChild(containerElem);

        if (selectedUrl == key) {
            selectUrl(selectedUrl);
        }
    }
}

function toggleFalsePositive(url) {
    storage.get(url).truePositive = !storage.get(url).truePositive;
}

function addUrl(flowData) {
    const data = {
        url: flowData["url"],
        method: flowData["method"],
        status: flowData["status"],
        originalRequest: flowData["original-request"],
        originalResponse: flowData["original-response"],
        replayRequest: flowData["replay-request"],
        replayResponse: "",
        truePositive: false,
    }

    const flow = flowData["flow-name"];
    storage.set(flow, data);

    renderUrls();
}

function selectUrl(url) {
    document.getElementById(selectedUrl ? selectedUrl : "this-should-never-be-a-html-id")?.classList.remove("selected-url");
    selectedUrl = url;
    document.getElementById(selectedUrl).classList.add("selected-url");

    // Content change
    const originalResponseElem = document.getElementById("original-response-iframe");
    const originalRawRequestElem = document.getElementById("original-raw-request");
    const originalRawResponseElem = document.getElementById("original-raw-response");
    const replayResponseElem = document.getElementById("replay-response-iframe");
    const replayRawRequestElem = document.getElementById("replay-raw-request");
    const replayRawResponseElem = document.getElementById("replay-raw-response");
    
    const originalResponse = storage.get(selectedUrl)["originalResponse"].split("\r\n\r\n")[1];
    const originalRawRequest = storage.get(selectedUrl)["originalRequest"];
    const originalRawResponse = storage.get(selectedUrl)["originalResponse"];
    const replayResponse = storage.get(selectedUrl)["replayResponse"].split("\r\n\r\n")[1];
    const replayRawRequest = storage.get(selectedUrl)["replayRequest"];
    const replayRawResponse = storage.get(selectedUrl)["replayResponse"];

    originalResponseElem.srcdoc = originalResponse;
    originalRawRequestElem.value = originalRawRequest;
    originalRawResponseElem.value = originalRawResponse;
    replayResponseElem.srcdoc = replayResponse;
    replayRawRequestElem.value = replayRawRequest;
    replayRawResponseElem.value = replayRawResponse;

    renderResponsesMenus(url);
    showOriginalResponse();
    showReplayResponse();
}

function renderResponsesMenus(url) {
    // Change the menu-url for the original request
    let status = "";
    if (storage.get(url).status == "not replayed") {
        status = "status-a";
    } else if (storage.get(url).status == "same response") {
        status = "status-b";
    } else if (storage.get(url).status == "different responses") {
        status = "status-c";
    } else if (storage.get(url).status == "replaying") {
        status = "status-d";
    }
    const originalMenuUrlElem = document.getElementById("original-menu-url");
    originalMenuUrlElem.classList.remove("none", "status-a", "status-b", "status-c", "status-d");
    originalMenuUrlElem.classList.add(status);
    originalMenuUrlElem.innerHTML = storage.get(url).url;
    originalMenuUrlElem.title = storage.get(url).url;

    // Change the menu-url for the replayed request
    // TODO: change this to the real replayed url
    const replayMenuUrlElem = document.getElementById("replay-menu-url");
    replayMenuUrlElem.classList.remove("none", "status-a", "status-b", "status-c", "status-d");
    replayMenuUrlElem.classList.add(status);
    replayMenuUrlElem.innerHTML = storage.get(url).url;
    replayMenuUrlElem.title = storage.get(url).url;

    const replayButtonElem = document.getElementById("replay-button");
    if (storage.get(url).status == "not replayed") {
        replayButtonElem.classList.add("temp-button");
        replayButtonElem.classList.remove("replaying");
        replayButtonElem.setAttribute("onclick", `replayRequest('${url}')`);
        replayButtonElem.innerText = "Repetir";
    } else if (storage.get(url).status == "replaying") {
        replayButtonElem.classList.remove("temp-button");
        replayButtonElem.classList.add("replaying");
        replayButtonElem.setAttribute("onclick", "");
        replayButtonElem.innerText = "Repetindo";
    } else {
        replayButtonElem.classList.remove("temp-button");
        replayButtonElem.classList.remove("replaying");
        replayButtonElem.setAttribute("onclick", "");
        replayButtonElem.innerText = "Repetido";
    }
}

function showOriginalResponse() {
    // Buttons
    const originalResponseButtonElem = document.getElementById("original-response-button");
    const originalRawRequestButtonElem = document.getElementById("original-raw-request-button");
    const originalRawResponseButtonElem = document.getElementById("original-raw-response-button");
    
    // Content
    const originalResponseElem = document.getElementById("original-response-iframe");
    const originalRawRequestElem = document.getElementById("original-raw-request");
    const originalRawResponseElem = document.getElementById("original-raw-response");
    
    originalResponseButtonElem.classList.add("selected-button");
    originalRawRequestButtonElem.classList.remove("selected-button");
    originalRawResponseButtonElem.classList.remove("selected-button");

    originalResponseElem.classList.remove("none");
    originalRawRequestElem.classList.add("none");
    originalRawResponseElem.classList.add("none");
}

function showOriginalRawRequest() {
    // Buttons
    const originalResponseButtonElem = document.getElementById("original-response-button");
    const originalRawRequestButtonElem = document.getElementById("original-raw-request-button");
    const originalRawResponseButtonElem = document.getElementById("original-raw-response-button");

    // Content
    const originalResponseElem = document.getElementById("original-response-iframe");
    const originalRawRequestElem = document.getElementById("original-raw-request");
    const originalRawResponseElem = document.getElementById("original-raw-response");

    originalResponseButtonElem.classList.remove("selected-button");
    originalRawRequestButtonElem.classList.add("selected-button");
    originalRawResponseButtonElem.classList.remove("selected-button");

    originalResponseElem.classList.add("none");
    originalRawRequestElem.classList.remove("none");
    originalRawResponseElem.classList.add("none");
}

function showOriginalRawResponse() {
    // Buttons
    const originalResponseButtonElem = document.getElementById("original-response-button");
    const originalRawRequestButtonElem = document.getElementById("original-raw-request-button");
    const originalRawResponseButtonElem = document.getElementById("original-raw-response-button");

    // Content
    const originalResponseElem = document.getElementById("original-response-iframe");
    const originalRawRequestElem = document.getElementById("original-raw-request");
    const originalRawResponseElem = document.getElementById("original-raw-response");

    originalResponseButtonElem.classList.remove("selected-button");
    originalRawRequestButtonElem.classList.remove("selected-button");
    originalRawResponseButtonElem.classList.add("selected-button");

    originalResponseElem.classList.add("none");
    originalRawRequestElem.classList.add("none");
    originalRawResponseElem.classList.remove("none");
}

function showReplayResponse() {
    // Buttons
    const replayResponseButtonElem = document.getElementById("replay-response-button");
    const replayRawRequestButtonElem = document.getElementById("replay-raw-request-button");
    const replayRawResponseButtonElem = document.getElementById("replay-raw-response-button");
    
    // Content
    const replayResponseElem = document.getElementById("replay-response-iframe");
    const replayRawRequestElem = document.getElementById("replay-raw-request");
    const replayRawResponseElem = document.getElementById("replay-raw-response");
    
    replayResponseButtonElem.classList.add("selected-button");
    replayRawRequestButtonElem.classList.remove("selected-button");
    replayRawResponseButtonElem.classList.remove("selected-button");

    replayResponseElem.classList.remove("none");
    replayRawRequestElem.classList.add("none");
    replayRawResponseElem.classList.add("none");
}

function showReplayRawRequest() {
    // Buttons
    const replayResponseButtonElem = document.getElementById("replay-response-button");
    const replayRawRequestButtonElem = document.getElementById("replay-raw-request-button");
    const replayRawResponseButtonElem = document.getElementById("replay-raw-response-button");

    // Content
    const replayResponseElem = document.getElementById("replay-response-iframe");
    const replayRawRequestElem = document.getElementById("replay-raw-request");
    const replayRawResponseElem = document.getElementById("replay-raw-response");

    replayResponseButtonElem.classList.remove("selected-button");
    replayRawRequestButtonElem.classList.add("selected-button");
    replayRawResponseButtonElem.classList.remove("selected-button");

    replayResponseElem.classList.add("none");
    replayRawRequestElem.classList.remove("none");
    replayRawResponseElem.classList.add("none");
}

function showReplayRawResponse() {
    // Buttons
    const replayResponseButtonElem = document.getElementById("replay-response-button");
    const replayRawRequestButtonElem = document.getElementById("replay-raw-request-button");
    const replayRawResponseButtonElem = document.getElementById("replay-raw-response-button");

    // Content
    const replayResponseElem = document.getElementById("replay-response-iframe");
    const replayRawRequestElem = document.getElementById("replay-raw-request");
    const replayRawResponseElem = document.getElementById("replay-raw-response");

    replayResponseButtonElem.classList.remove("selected-button");
    replayRawRequestButtonElem.classList.remove("selected-button");
    replayRawResponseButtonElem.classList.add("selected-button");

    replayResponseElem.classList.add("none");
    replayRawRequestElem.classList.add("none");
    replayRawResponseElem.classList.remove("none");
}

function toggleStatus(url, status) {
    const elem = document.getElementById(url);
    if (!elem) return;
    
    const button = elem.children[0];

    elem.classList.toggle(status);
    
    let nextStatus = ""
    if (status === "status-a") {
        nextStatus = "status-b";
    } else if (status === "status-b") {
        nextStatus = "status-c";
    } else if (status === "status-c") {
        nextStatus = "status-a";
    }
    
    button.onclick = () => toggleStatus(url, nextStatus);
    elem.classList.toggle(nextStatus);
}