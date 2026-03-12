const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === "timer") {
        console.log("⏰ Timer update:", data.content);
        // You could update a clock on your webpage here
    } else if (data.type === "echo") {
        console.log("💬 Server acknowledged your message!");
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

// Test sending a message after 5 seconds
setTimeout(() => {
    socket.send(JSON.stringify({ event: "New Session", text: "[*] Starting a new session." }));

}, 1000);

// const socket = new WebSocket('ws://localhost:8765');

// socket.onmessage = function(event) {
//     const data = JSON.parse(event.data);
//     data["status"] = "status-a";
//     addUrl(data);
// };

// socket.onopen = () => console.log('Connected to Python Backend');
// socket.onclose = () => console.log('Disconnected');

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

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

let responses = {
    original: {},
    replay: {},
};
let urlCount = 0;
function addUrl(flowData) {
    const url = flowData["url"];
    const method = flowData["method"];
    const status = flowData["status"];
    const originalResponse = flowData["originalResponse"];
    const replayResponse = flowData["replayResponse"];
    const id = `url-${urlCount}`;
    urlCount += 1;

    // Save the responses for later
    responses.original[id] = originalResponse;
    responses.replay[id] = replayResponse;

    // Create the container
    const container = document.createElement('div');
    container.className = `url ${status}`;
    container.id = id;
    container.setAttribute('onclick', `selectUrl('${id}')`);

    // Inject the inner HTML
    container.innerHTML = `
        <span class="status-button" onclick='toggleStatus("${id}", "${status}")'></span>
        <span class="http-verb http-${method.toLowerCase()}">${method}</span>
        <span class="url-text truncate">${url}</span>
    `;

    // Append the container
    const urls = document.getElementById("urls");
    urls.appendChild(container);
}

async function asyncAddUrl(flowData, time) {
    await sleep(time);
    // console.log(time);
    addUrl(flowData);
}

// for (const flowData of mockData) {
//     // addUrl(flowData);

//     const time = 15 * Math.floor(Math.random() * 1000);
//     asyncAddUrl(flowData, time);
// }

let selectedUrl = "";
function selectUrl(url) {
    document.getElementById(selectedUrl ? selectedUrl : "this-should-never-be-a-html-id")?.classList.toggle("selected-url");
    selectedUrl = url;
    document.getElementById(selectedUrl).classList.toggle("selected-url");

    const originalResponse = responses.original[url];
    const originalResponseContentElem = document.getElementById("original-response-content");
    originalResponseContentElem.replaceChildren();
    renderJSON(JSON.parse(originalResponse), originalResponseContentElem, 0);

    const replayResponse = responses.replay[url];
    const replayesponseContentElem = document.getElementById("replay-response-content");
    replayesponseContentElem.replaceChildren();
    renderJSON(JSON.parse(replayResponse), replayesponseContentElem, 0);
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