/* Knowledge Base Assistant */
const API_BASE_URL = "http://127.0.0.1:8000/new-knowledge-base";
// const API_BASE_URL = "https://knowledgebasebackend-production.up.railway.app"

const processBtn = document.getElementById("processBtn");
const processUrlBtn = document.getElementById("processUrlBtn");
const addUrlsBtn = document.getElementById("addUrlsBtn");
const saveUrlsBtn = document.getElementById("saveUrlsBtn");
const cancelUrlsBtn = document.getElementById("cancelUrlsBtn");
const sendBtn = document.getElementById("sendBtn");
const newConversationBtn = document.getElementById("newConversationBtn");
const fileUpload = document.getElementById("fileUpload");
const urlInput = document.getElementById("urlInput");
const chatInput = document.getElementById("chatInput");
const chatBox = document.getElementById("chatBox");
const fileListDiv = document.getElementById("fileList");
const urlListDiv = document.getElementById("urlList");
const urlModal = document.getElementById("urlModal");
const domainPrompt = document.getElementById("domainPrompt");
const doneBtn = document.getElementById("doneBtn");
const clearIndexBtn = document.getElementById("clearIndexBtn");
const fileSpinner = document.getElementById("fileSpinner");
const urlSpinner = document.getElementById("urlSpinner");
const doneSpinner = document.getElementById("doneSpinner");
const clearStatus = document.getElementById("clearStatus");
const fileStatus = document.getElementById("fileStatus");
const urlStatus = document.getElementById("urlStatus");
const doneStatus = document.getElementById("doneStatus");
const convIdDisplay = document.getElementById("convIdDisplay");

let conversation = [
  { role: "assistant", content: "Hello! I'm here to help you with internal knowledge and data analysis. What would you like to know?" }
];
let urlList = [];
let conversationId = localStorage.getItem("conversationId") || null;




// Simple Markdown to HTML
// function simpleMarkdownToHtml(text) {
//   if (!text) return '';
//   let html = text
//     .replace(/&/g, '&amp;')
//     .replace(/</g, '&lt;')
//     .replace(/>/g, '&gt;');
//   const lines = html.split('\n');
//   html = '';
//   let inList = false;
//   let listType = '';
//   lines.forEach(line => {
//     if (line.trim() === '') {
//       if (inList) { html += `</${listType}>\n`; inList = false; }
//       return;
//     }
//     line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
//     line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');
//     if (line.startsWith('# ')) {
//       if (inList) { html += `</${listType}>\n`; inList = false; }
//       html += `<h1>${line.slice(2).trim()}</h1>\n`;
//     } else if (line.startsWith('## ')) {
//       if (inList) { html += `</${listType}>\n`; inList = false; }
//       html += `<h2>${line.slice(3).trim()}</h2>\n`;
//     } else if (line.match(/^\d+\. /)) {
//       const content = line.replace(/^\d+\. /, '').trim();
//       if (!inList || listType !== 'ol') {
//         if (inList) html += `</${listType}>\n`;
//         html += '<ol>\n'; listType = 'ol'; inList = true;
//       }
//       html += `<li>${content}</li>\n`;
//     } else if (line.startsWith('- ') || line.startsWith('* ')) {
//       if (!inList || listType !== 'ul') {
//         if (inList) html += `</${listType}>\n`;
//         html += '<ul>\n'; listType = 'ul'; inList = true;
//       }
//       html += `<li>${line.slice(2).trim()}</li>\n`;
//     } else {
//       if (inList) { html += `</${listType}>\n`; inList = false; }
//       html += `<p>${line.trim()}</p>\n`;
//     }
//   });
//   if (inList) html += `</${listType}>\n`;
//   return html.trim();
// } 





// Render chat
// function renderConversation() {
//   chatBox.innerHTML = "";
//   conversation.forEach(msg => {
//     const div = document.createElement("div");
//     div.className = `chat-message ${msg.role}`;
//     div.innerHTML = simpleMarkdownToHtml(msg.content);
//     chatBox.appendChild(div);
//   });
//   chatBox.scrollTop = chatBox.scrollHeight;
// }
// renderConversation();


/* -------------------------------------------------
   Existing code (keep everything up to the
   simpleMarkdownToHtml function)
   ------------------------------------------------- */

let chartCounter = 0;   // unique id for each chart

// ────── 1. ENHANCED MARKDOWN → HTML  ──────
function simpleMarkdownToHtml(text) {
    if (!text) return '';

    // Escape HTML first
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const lines = html.split('\n');
    let output = '';
    let inList = false;
    let listType = '';

    // ---- Helper to close open list ----
    const closeList = () => {
        if (inList) {
            output += `</${listType}>\n`;
            inList = false;
        }
    };

    // ---- Table state ----
    let inTable = false;
    let tableHeader = '';
    let tableBody = '';

    lines.forEach((rawLine, idx) => {
        let line = rawLine.trimEnd();

        // ---- Empty line ----
        if (!line) {
            closeList();
            if (inTable) {
                output += `<div class="table-wrapper"><table><thead><tr>${tableHeader}</tr></thead><tbody>${tableBody}</tbody></table></div>\n`;
                inTable = false; tableHeader = ''; tableBody = '';
            }
            output += '<br>';
            return;
        }

        // ---- Bold / Italic ----
        line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // ---- Headers ----
        if (line.startsWith('# ')) {
            closeList(); if (inTable) { /* finish table */ }
            output += `<h1>${line.slice(2).trim()}</h1>\n`;
            return;
        }
        if (line.startsWith('## ')) {
            closeList();
            output += `<h2>${line.slice(3).trim()}</h2>\n`;
            return;
        }

        // ---- Lists ----
        if (line.match(/^\d+\.\s/)) {
            const content = line.replace(/^\d+\.\s/, '');
            if (!inList || listType !== 'ol') { closeList(); output += '<ol>\n'; listType = 'ol'; inList = true; }
            output += `<li>${content}</li>\n`;
            return;
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
            const content = line.slice(2);
            if (!inList || listType !== 'ul') { closeList(); output += '<ul>\n'; listType = 'ul'; inList = true; }
            output += `<li>${content}</li>\n`;
            return;
        }

        // ---- TABLE detection (markdown pipe table) ----
        // Header row: | col | col |
        // Separator : | --- | --- |
        // Body rows: | val | val |
        if (line.includes('|')) {
            const cells = line.split('|').map(c => c.trim()).filter(c => c);
            if (cells.length > 1) {
                // First row of a new table?
                if (!inTable) {
                    closeList();
                    inTable = true;
                }

                // Detect separator line (contains only -,:,)
                const isSeparator = cells.every(c => /^[:\-]+$/g.test(c));
                if (isSeparator && tableHeader === '') {
                    // previous line was header
                    return;                 // ignore separator
                }

                const rowHtml = cells.map(c => `<td>${c}</td>`).join('');
                if (tableHeader === '') {
                    tableHeader = cells.map(c => `<th>${c}</th>`).join('');
                } else {
                    tableBody += `<tr>${rowHtml}</tr>`;
                }
                return;
            }
        }

        // ---- Anything else → paragraph (or finish table) ----
        closeList();
        if (inTable) {
            output += `<div class="table-wrapper"><table><thead><tr>${tableHeader}</tr></thead><tbody>${tableBody}</tbody></table></div>\n`;
            inTable = false; tableHeader = ''; tableBody = '';
        }
        output += `<p>${line}</p>\n`;
    });

    // ---- Final clean-up ----
    closeList();
    if (inTable) {
        output += `<div class="table-wrapper"><table><thead><tr>${tableHeader}</tr></thead><tbody>${tableBody}</tbody></table></div>\n`;
    }

    return output.trim();
}

// ────── 2. SUMMARY + CHART DETECTION  ──────
function postProcessAssistantHTML(html) {
    // 1. Look for a **summary** block: ```summary ... ```
    const summaryReg = /```summary\s*([\s\S]*?)\s*```/i;
    const summaryMatch = html.match(summaryReg);
    let finalHTML = html;

    if (summaryMatch) {
        const summaryText = summaryMatch[1].trim();
        const summaryBox = `<div class="summary-box"><strong>Summary:</strong> ${summaryText}</div>`;
        finalHTML = finalHTML.replace(summaryReg, summaryBox);
    }

    // 2. Look for **Highcharts JSON** blocks: ```chart { ... } ```
    const chartReg = /```chart\s*(\{[\s\S]*?\})\s*```/gi;
    finalHTML = finalHTML.replace(chartReg, (match, jsonStr) => {
        try {
            const config = JSON.parse(jsonStr);
            const chartId = `chart-${++chartCounter}`;
            setTimeout(() => Highcharts.chart(chartId, config), 0);
            return `<div id="${chartId}" class="chart-container"></div>`;
        } catch (e) {
            return `<pre>Invalid chart JSON</pre>`;
        }
    });

    return finalHTML;
}

// ────── 3. RENDER CHAT (use post-process)  ──────
function renderConversation() {
    chatBox.innerHTML = "";
    conversation.forEach(msg => {
        const div = document.createElement("div");
        div.className = `chat-message ${msg.role}`;

        let processed = simpleMarkdownToHtml(msg.content);
        if (msg.role === "assistant") {
            processed = postProcessAssistantHTML(processed);
        }
        div.innerHTML = processed;
        chatBox.appendChild(div);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}
renderConversation();

/* -------------------------------------------------
   The rest of your script (file upload, URLs,
   sendMessage, etc.) stays **exactly** the same.
   ------------------------------------------------- */


// File validation
fileUpload.addEventListener("change", () => {
  fileListDiv.innerHTML = "";
  const files = fileUpload.files;
  const validExt = ['.pdf', '.txt', '.csv', '.xlsx', '.xls'];
  const validFiles = [];
  const invalidFiles = [];

  for (let file of files) {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (validExt.includes(ext)) {
      validFiles.push(file);
    } else {
      invalidFiles.push(file.name);
    }
  }

  if (invalidFiles.length > 0) {
    fileStatus.textContent = `Invalid file(s): ${invalidFiles.join(', ')}. Use PDF, TXT, CSV, XLSX.`;
    fileStatus.style.color = '#dc2626';
    fileListDiv.textContent = validFiles.length > 0 ? "" : "No valid files.";
  } else {
    fileStatus.textContent = "";
  }

  if (validFiles.length > 0) {
    const ul = document.createElement("ul");
    validFiles.forEach(file => {
      const li = document.createElement("li");
      li.textContent = file.name;
      ul.appendChild(li);
    });
    fileListDiv.appendChild(ul);
  } else if (invalidFiles.length === 0) {
    fileListDiv.textContent = "No file selected.";
  }
});

// URLs
function renderUrlList() {
  urlListDiv.innerHTML = urlList.length > 0
    ? `<ul>${urlList.map(u => `<li>${u}</li>`).join('')}</ul>`
    : "No URLs added.";
}
renderUrlList();

addUrlsBtn.addEventListener("click", () => {
  urlModal.style.display = "block";
  urlInput.value = urlList.join("\n");
});

saveUrlsBtn.addEventListener("click", () => {
  urlList = urlInput.value.trim().split("\n").map(u => u.trim()).filter(u => u);
  renderUrlList();
  urlModal.style.display = "none";
  urlStatus.textContent = `${urlList.length} URLs added. Click 'Process URLs'.`;
});

cancelUrlsBtn.addEventListener("click", () => {
  urlModal.style.display = "none";
});

// Process Files
processBtn.addEventListener("click", async () => {
  const files = fileUpload.files;
  if (!files.length) {
    fileStatus.textContent = "Please select files first.";
    fileStatus.style.color = '#dc2626';
    return;
  }

  const formData = new FormData();
  for (let file of files) formData.append("files", file);
  formData.append("clear_index", "false");

  fileStatus.textContent = "Uploading and processing...";
  fileStatus.style.color = '#10b981';
  fileSpinner.style.display = "inline-block";
  convIdDisplay.style.display = "none";

  try {
    const res = await fetch(`${API_BASE_URL}/upload_files`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.conversation_id) {
    convIdDisplay.style.display = "block";
    convIdDisplay.textContent = `Conversation ID: ${data.conversation_id} (use for data queries)`;
    localStorage.setItem("lastDataConvId", data.conversation_id);
    }

    fileStatus.textContent = data.message || data.error || "Done.";
    fileStatus.style.color = data.error ? '#dc2626' : '#10b981';
  } catch (err) {
    fileStatus.textContent = "Connection error.";
    fileStatus.style.color = '#dc2626';
  } finally {
    fileSpinner.style.display = "none";
  }
});

// Process URLs
processUrlBtn.addEventListener("click", async () => {
  if (!urlList.length) {
    urlStatus.textContent = "Add URLs first.";
    urlStatus.style.color = '#dc2626';
    return;
  }
  const formData = new FormData();
  formData.append("urls", urlList.join(","));
  formData.append("clear_index", "false");

  urlStatus.textContent = "Processing URLs...";
  urlStatus.style.color = '#10b981';
  urlSpinner.style.display = "inline-block";

  try {
    const res = await fetch(`${API_BASE_URL}/upload_url`, { method: "POST", body: formData });
    const data = await res.json();
    urlStatus.textContent = data.message || data.error;
    urlStatus.style.color = data.error ? '#dc2626' : '#10b981';
  } catch {
    urlStatus.textContent = "Connection error.";
    urlStatus.style.color = '#dc2626';
  } finally {
    urlSpinner.style.display = "none";
  }
});

// Clear Index
clearIndexBtn.addEventListener("click", async () => {
  clearStatus.textContent = "Clearing...";
  clearStatus.style.color = '#10b981';
  try {
    const res = await fetch(`${API_BASE_URL}/clear_index`, { method: "POST" });
    const data = await res.json();
    clearStatus.textContent = data.message || data.error;
    clearStatus.style.color = data.error ? '#dc2626' : '#10b981';
  } catch {
    clearStatus.textContent = "Error.";
    clearStatus.style.color = '#dc2626';
  }
});

// Set Config
doneBtn.addEventListener("click", async () => {
  const config = { domain_instructions: domainPrompt.value.trim() };
  doneStatus.textContent = "Applying...";
  doneStatus.style.color = '#10b981';
  doneSpinner.style.display = "inline-block";

  try {
    const res = await fetch(`${API_BASE_URL}/set_config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config)
    });
    const data = await res.json();
    doneStatus.textContent = data.message || data.error;
    doneStatus.style.color = data.error ? '#dc2626' : '#10b981';
  } catch {
    doneStatus.textContent = "Error.";
    doneStatus.style.color = '#dc2626';
  } finally {
    doneSpinner.style.display = "none";
  }
});

// Send Message
async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question) return;

  conversation.push({ role: "user", content: question });
  renderConversation();
  chatInput.value = "";

  conversation.push({ role: "assistant", content: "Thinking..." });
  renderConversation();

  const payload = { question };
  if (conversationId) payload.conversation_id = conversationId;
  // Auto-use last data conv ID if no current conversation
  else if (localStorage.getItem("lastDataConvId")) {
    payload.conversation_id = localStorage.getItem("lastDataConvId");
    console.log("Using last data conv ID:", payload.conversation_id);
  }

  try {
    const res = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    conversation.pop(); // Remove "Thinking..."

    if (data.answer) {
      conversation.push({ role: "assistant", content: data.answer });
      if (data.conversation_id) {
        conversationId = data.conversation_id;
        localStorage.setItem("conversationId", conversationId);
      }
    } else {
      conversation.push({ role: "assistant", content: data.error || "No response." });
    }
  } catch (err) {
    conversation.pop();
    conversation.push({ role: "assistant", content: "Connection error." });
  }
  renderConversation();
}

sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });

// New Conversation
newConversationBtn.addEventListener("click", () => {
  conversationId = null;
  localStorage.removeItem("conversationId");
  conversation = [{ role: "assistant", content: "New conversation started. How can I help?" }];
  renderConversation();
  doneStatus.textContent = "New conversation started.";
  doneStatus.style.color = '#10b981';
});

// Default domain prompt
domainPrompt.value = `You are assisting with an internal knowledge base for a technology company.  
Assist employees with:
- Finding technical documentation (e.g., API guides, system architecture)
- Explaining company policies (e.g., HR, IT, security)
- Providing project-related information (e.g., timelines, resources)
- Answering FAQs about internal tools and processes  
Tone: Professional, technical, and concise.`;