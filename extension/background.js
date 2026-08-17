chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "download") {
        fetch("http://localhost:6578/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: request.url,
                type: request.type,
                resolution: request.resolution,
                separate_subs: request.separate_subs
            })
        })
        .then(res => res.json())
        .then(data => sendResponse({status: "success"}))
        .catch(err => sendResponse({status: "error"}));
        return true;
    }
    
    if (request.action === "fetch_info") {
        fetch("http://localhost:6578/fetch_info", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: request.url })
        })
        .then(res => res.json())
        .then(data => sendResponse(data))
        .catch(err => sendResponse({error: "Server offline"}));
        return true;
    }
});
