/*  Final MVP 3 */
const API_BASE_URL = "http://127.0.0.1:8000/customer-support"; // Match backend address
//const API_BASE_URL = "https://customersupportbackend-production.up.railway.app" // railway deploy url
const processBtn = document.getElementById("processBtn");
const processUrlBtn = document.getElementById("processUrlBtn");
const addUrlsBtn = document.getElementById("addUrlsBtn");
const saveUrlsBtn = document.getElementById("saveUrlsBtn");
const cancelUrlsBtn = document.getElementById("cancelUrlsBtn");
const sendBtn = document.getElementById("sendBtn");
const newConversationBtn = document.getElementById("newConversationBtn");
const pdfUpload = document.getElementById("pdfUpload");
const urlInput = document.getElementById("urlInput");
const chatInput = document.getElementById("chatInput");
const chatBox = document.getElementById("chatBox");
const fileListDiv = document.getElementById("fileList");
const urlListDiv = document.getElementById("urlList");
const urlModal = document.getElementById("urlModal");
const domainPrompt = document.getElementById("domainPrompt");
const doneBtn = document.getElementById("doneBtn");
const clearIndexBtn = document.getElementById("clearIndexBtn");
const pdfSpinner = document.getElementById("pdfSpinner");
const urlSpinner = document.getElementById("urlSpinner");
const doneSpinner = document.getElementById("doneSpinner");
const clearStatus = document.getElementById("clearStatus");
const pdfStatus = document.getElementById("pdfStatus");
const urlStatus = document.getElementById("urlStatus");
const doneStatus = document.getElementById("doneStatus");

let conversation = [
  { role: "assistant", content: "Hi there! How can I assist you with customer support today?" }
];
let urlList = []; // Store URLs entered by the user
let conversationId = localStorage.getItem("conversationId") || null; // Persist conversation ID



/* start  */ 

// Simple Markdown to HTML converter (handles bold, italics, headings, lists, paragraphs)
function simpleMarkdownToHtml(text) {
  if (!text) return '';

  // Escape HTML entities to prevent injection
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const lines = html.split('\n');
  html = '';
  let inList = false;
  let listType = '';

  lines.forEach(line => {
    if (line.trim() === '') {
      if (inList) {
        html += `</${listType}>\n`;
        inList = false;
      }
      return; // Skip empty lines, no extra <p>
    }

    // Inline formatting: bold and italics
    line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Headings
    if (line.startsWith('# ')) {
      if (inList) {
        html += `</${listType}>\n`;
        inList = false;
      }
      html += `<h1>${line.slice(2).trim()}</h1>\n`;
      return;
    } else if (line.startsWith('## ')) {
      if (inList) {
        html += `</${listType}>\n`;
        inList = false;
      }
      html += `<h2>${line.slice(3).trim()}</h2>\n`;
      return;
    }

    // Convert numbered lists to unordered lists
    if (line.match(/^\d+\. /)) {
      const content = line.replace(/^\d+\. /, '').trim();

      if (!inList || listType !== 'ul') {
        if (inList) html += `</${listType}>\n`;
        html += '<ul>\n';
        listType = 'ul';
        inList = true;
      }
      html += `<li>${content}</li>\n`;
      return;
    }

    // Unordered lists
    if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList || listType !== 'ul') {
        if (inList) html += `</${listType}>\n`;
        html += '<ul>\n';
        listType = 'ul';
        inList = true;
      }
      html += `<li>${line.slice(2).trim()}</li>\n`;
      return;
    }

    // Paragraphs (default)
    if (inList) {
      html += `</${listType}>\n`;
      inList = false;
    }
    html += `<p>${line.trim()}</p>\n`;
  });

  if (inList) html += `</${listType}>\n`;

  return html.trim();
}

/* end  */ 


// Render conversation
function renderConversation() {
  chatBox.innerHTML = "";
  conversation.forEach(msg => {
    const div = document.createElement("div");
    div.className = `chat-message ${msg.role}`;
    div.innerHTML = simpleMarkdownToHtml(msg.content); // handling the format of the answer 
   // div.textContent = msg.content;  // old when markdown not handled
    chatBox.appendChild(div);
  });
  chatBox.scrollTop = chatBox.scrollHeight;
}
renderConversation();

// Show selected file names
pdfUpload.addEventListener("change", () => {
  fileListDiv.innerHTML = "";
  if (pdfUpload.files.length > 0) {
    const ul = document.createElement("ul");
    for (let file of pdfUpload.files) {
      const li = document.createElement("li");
      li.textContent = file.name;
      ul.appendChild(li);
    }
    fileListDiv.appendChild(ul);
  } else {
    fileListDiv.textContent = "No file selected.";
  }
});

// Show added URLs
function renderUrlList() {
  urlListDiv.innerHTML = "";
  if (urlList.length > 0) {
    const ul = document.createElement("ul");
    urlList.forEach(url => {
      const li = document.createElement("li");
      li.textContent = url;
      ul.appendChild(li);
    });
    urlListDiv.appendChild(ul);
  } else {
    urlListDiv.textContent = "No URLs added.";
  }
}
renderUrlList();

// Open URL modal
addUrlsBtn.addEventListener("click", () => {
  urlModal.style.display = "block";
  urlInput.value = urlList.join("\n"); // Pre-fill with existing URLs
});

// Save URLs from modal
saveUrlsBtn.addEventListener("click", () => {
  const urls = urlInput.value.trim().split("\n").map(url => url.trim()).filter(url => url);
  urlList = urls;
  renderUrlList();
  urlModal.style.display = "none";
  urlStatus.textContent = `${urls.length} URLs added. Click 'Process URLs' to fetch content.`;
});

// Cancel URL input
cancelUrlsBtn.addEventListener("click", () => {
  urlModal.style.display = "none";
  urlInput.value = "";
});

// Upload & process PDFs with spinner
processBtn.addEventListener("click", async () => {
  const files = pdfUpload.files;
  if (!files.length) {
    pdfStatus.textContent = "Please select PDF files first.";
    return;
  }

  const formData = new FormData();
  for (let file of files) {
    formData.append("pdf_files", file);
  }
  formData.append("clear_index", "false");

  pdfStatus.textContent = "Uploading and processing PDFs...";
  pdfSpinner.style.display = "inline-block"; // Show PDF spinner

  try {
    const res = await fetch(`${API_BASE_URL}/upload_pdf`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    pdfStatus.textContent = data.message || data.error;
  } catch (err) {
    pdfStatus.textContent = "Error connecting to server.";
  } finally {
    pdfSpinner.style.display = "none"; // Hide PDF spinner
  }
});

// Upload & process URLs
processUrlBtn.addEventListener("click", async () => {
  if (!urlList.length) {
    urlStatus.textContent = "Please add URLs first.";
    return;
  }

  const urls = urlList.join(",");
  const formData = new FormData();
  formData.append("urls", urls);
  formData.append("clear_index", "false");

  urlStatus.textContent = "Uploading and processing URLs...";
  urlSpinner.style.display = "inline-block"; // Show URL spinner

  try {
    const res = await fetch(`${API_BASE_URL}/upload_url`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.status === 403 && data.error === "Website owner does not allow content access") {
      urlStatus.textContent = "Website owner does not allow access to the content.";
    } else {
      urlStatus.textContent = data.message || data.error;
    }
  } catch (err) {
    urlStatus.textContent = "Error connecting to server.";
  } finally {
    urlSpinner.style.display = "none"; // Hide URL spinner
  }
});

// Clear vector index
clearIndexBtn.addEventListener("click", async () => {
  clearStatus.textContent = "Clearing vector index...";
  try {
    const res = await fetch(`${API_BASE_URL}/clear_index`, {
      method: "POST"
    });
    const data = await res.json();
    clearStatus.textContent = data.message || data.error;
  } catch (err) {
    clearStatus.textContent = "Error clearing index.";
  }
});

// Send chat message
sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

// Start new conversation
newConversationBtn.addEventListener("click", () => {
  conversationId = null; // Reset conversation ID
  localStorage.removeItem("conversationId"); // Clear from localStorage
  conversation = [{ role: "assistant", content: "Hi there! How can I assist you with customer support today?" }]; // Reset conversation
  renderConversation();
  doneStatus.textContent = "Started a new conversation.";
});

doneBtn.addEventListener("click", async () => {
  const config = {
    domain_instructions: domainPrompt.value.trim()
  };
  doneStatus.textContent = "Applying configuration...";
  doneSpinner.style.display = "inline-block"; // Show Done spinner
  try {
    const res = await fetch(`${API_BASE_URL}/set_config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config)
    });
    const data = await res.json();
    doneStatus.textContent = data.message;
  } catch (err) {
    doneStatus.textContent = "Error applying configuration.";
  } finally {
    doneSpinner.style.display = "none"; // Hide Done spinner
  }
});

// Optional: Pre-fill default medical instructions
domainPrompt.value = `You are supporting a medical clinic.  
Assist patients with:
- Booking appointments  
- Providing clinic hours and contact details  
- Explaining services (consultations, treatments, specialties)  
- Answering FAQs about medical staff, insurance, pricing  
- Redirecting emergencies to call emergency services immediately  

Tone: Empathetic, reassuring, and professional.`;

async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question) return;

  conversation.push({ role: "user", content: question });
  renderConversation();
  chatInput.value = "";

  conversation.push({ role: "assistant", content: "Fetching answer..." });
  renderConversation();

  try {
    const payload = { question };
    if (conversationId) payload.conversation_id = conversationId; // Only include if not null
    console.log("Sending payload to /ask:", JSON.stringify(payload)); // Debug payload
    const res = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errorData = await res.json();
      console.error("Error response from server:", errorData); // Debug error response
      conversation.pop();
      conversation.push({ role: "assistant", content: errorData.error || `Server error: ${res.status}` });
      doneStatus.textContent = errorData.error || "Failed to get response from server.";
    } else {
      const data = await res.json();
      conversation.pop();
      if (data.answer) {
        conversation.push({ role: "assistant", content: data.answer });
        // Store conversation_id from response
        if (data.conversation_id) {
          conversationId = data.conversation_id;
          localStorage.setItem("conversationId", conversationId);
        }
      } else {
        conversation.push({ role: "assistant", content: data.error || "No response from server." });
        doneStatus.textContent = data.error || "No response from server.";
      }
    }
  } catch (err) {
    console.error("Fetch error:", err); // Debug fetch error
    conversation.pop();
    conversation.push({ role: "assistant", content: "Error connecting to server." });
    doneStatus.textContent = "Error connecting to server.";
  }
  renderConversation();
}