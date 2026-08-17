function fetchDownloads() {
    fetch("http://localhost:6578/status")
        .then(response => response.json())
        .then(data => {
            const list = document.getElementById("downloads-list");
            if (data.length === 0) {
                list.innerHTML = "<p style='color:#666'>No active downloads</p>";
                return;
            }
            
            list.innerHTML = "";
            data.forEach(task => {
                const item = document.createElement("div");
                item.className = "download-item";
                
                let progress = task.progress || 0;
                let isComplete = task.status === "completed";
                let isError = task.status.startsWith("error");
                
                let barColor = isComplete ? "#4CAF50" : (isError ? "#f44336" : "#2196F3");
                
                item.innerHTML = `
                    <div class="filename" title="${task.filename}">${task.filename}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%; background: ${barColor}"></div>
                    </div>
                    <div class="details">
                        <span>${progress}%</span>
                        <span>${task.speed}</span>
                        <span>${task.status}</span>
                    </div>
                    <div class="controls" style="margin-top: 5px;">
                        ${!isComplete && !isError ? `<button onclick="action('${task.task_id}', 'pause')">Pause</button>
                        <button onclick="action('${task.task_id}', 'resume')">Resume</button>
                        <button onclick="action('${task.task_id}', 'cancel')">Cancel</button>` : ''}
                    </div>
                `;
                list.appendChild(item);
            });
        })
        .catch(err => {
            document.getElementById("downloads-list").innerHTML = "<p style='color:red'>Server offline. Start Python App.</p>";
        });
}

function action(taskId, actionType) {
    fetch(`http://localhost:6578/${actionType}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId })
    }).then(() => fetchDownloads());
}

// Refresh every second
setInterval(fetchDownloads, 1000);
fetchDownloads();
