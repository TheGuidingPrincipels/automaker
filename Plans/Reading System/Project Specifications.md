# **Project Specification: "DeepRead" (RSVP Reading System)**

## **1\. Executive Summary & Goal**

**Objective:** Develop a full-stack web application implementing the **Rapid Serial Visual Presentation (RSVP)** method. The system will ingest text documents (Markdown, PDF), parse them into tokenized streams, and display them one word at a time at high speeds (300–1000 WPM) on a high-contrast black interface.

Core Philosophy:  
The goal is to eliminate saccadic eye movements (the time wasted moving eyes between words). By presenting text at a fixed focal point (the "Optimal Recognition Point"), we increase reading speed while maintaining comprehension through algorithmic rhythm adjustments.

## **2\. Tech Stack Requirements**

* **Frontend:** Vue.js 3 (Composition API), TypeScript, Vite.  
* **State Management:** Pinia (for managing playback state, WPM, and current word index).  
* **Backend:** Python 3.11+ (FastAPI is preferred for async speed, or Flask).  
* **Styling:** Tailwind CSS (for rapid, high-contrast UI development).

## **3\. System Architecture**

### **3.1 Data Flow**

1. **Upload:** User uploads a file (.md, .txt, .pdf) via the Vue frontend.  
2. **Ingestion (Backend):** Python parses the file, strips formatting (while keeping structural pauses), and tokenizes the text.  
3. **Processing (Backend):** The text is converted into a structured JSON payload containing the word, its length, and a **delay multiplier** (see Section 4.2).  
4. **Display (Frontend):** The Vue client receives the JSON and renders the "Reader" component, handling the high-precision timing loop.

### **3.2 Data Structure (JSON Contract)**

The backend does not return a simple string. It returns an array of "Word Objects" to offload processing power from the client.

{  
  "meta": {  
    "title": "Document Name",  
    "total\_words": 5000  
  },  
  "content": \[  
    {  
      "id": 0,  
      "text": "The",  
      "delay\_multiplier": 1.0,  
      "orp\_index": 1  
    },  
    {  
      "id": 1,  
      "text": "algorithm",  
      "delay\_multiplier": 1.0,  
      "orp\_index": 4  
    },  
    {  
      "id": 2,  
      "text": "works.",  
      "delay\_multiplier": 2.5,  // Longer pause for period  
      "orp\_index": 2  
    }  
  \]  
}

## **4\. Feature Specifications (The "Rules")**

### **4.1 The Reader UI (Visuals)**

* **Canvas:** Full-screen viewport, pure black background (\#000000).  
* **Focal Point:** A persistent visual indicator (a red notch or reticle) at the top and bottom of the reading area to anchor the eye.  
* **Typography:** Monospace or high-legibility sans-serif (e.g., Roboto Mono, Inter). Text color: White or Light Gray (\#E5E5E5).  
* **ORP Alignment (CRITICAL):**  
  * The words must **not** be center-aligned.  
  * They must be aligned by their **Optimal Recognition Point (ORP)**.  
  * *Logic:* The ORP is typically the slightly-left-of-center character (approx 35% into the word).  
  * *Implementation:* The letter at the ORP index must always render at the exact distinct horizontal pixel center of the screen.

### **4.2 The Rhythm Algorithm (Variable Delay)**

To prevent cognitive overload, the system cannot display every word for the exact same duration.

* **Base Duration:** $T\_{base} \= 60,000 / WPM$.  
* **Punctuation Logic:**  
  * Period (.), Question (?), Exclamation (\!): **2.5x duration**.  
  * Comma (,), Semicolon (;), Colon (:): **1.5x duration**.  
  * Long words (\>8 chars): **1.2x duration**.  
  * Paragraph breaks: Insert an empty "blank" frame or **3.0x duration**.

### **4.3 Controls**

* **Scrubber:** A progress bar showing % completed.  
* **Speed Control:** Slider/Input for WPM (Range: 100 to 1000).  
* **Keyboard Shortcuts:**  
  * Space: Play/Pause.  
  * Left Arrow: Rewind 10 words (Context recovery).  
  * Right Arrow: Forward 10 words.  
  * Up/Down Arrow: Adjust WPM by ±25.

## **5\. Backend Logic (Python)**

### **5.1 File Parsing**

* **Markdown:** Use markdown library to convert to HTML, then BeautifulSoup to extract raw text, OR use regex to strip syntax (\*\*, \#\#, etc.) while preserving paragraph structure.  
* **PDF:** Use pypdf or pdfminer.six to extract text. Note: PDF extraction often breaks paragraphs; implementing a "sentence joiner" heuristic is necessary.

### **5.2 Tokenizer**

The Python tokenizer acts as the "Director." It iterates through the clean text string:

1. Splits by whitespace.  
2. Checks the last character for punctuation.  
3. Assigns the delay\_multiplier.  
4. Calculates the orp\_index (Algorithm: len(word) // 4 \+ 1 or similar heuristic).

## **6\. Frontend Logic (Vue.js/TS)**

### **6.1 The Timing Engine**

* **Do NOT use setInterval:** It drifts over time.  
* **Use requestAnimationFrame or a Delta-Time loop:**  
  * Calculate expected\_next\_frame\_time.  
  * If current\_time \>= expected\_next\_frame\_time: Render next word.  
* **Reactive WPM:** Changing WPM must immediately alter the T\_base for the *next* word displayed.

### **6.2 Component Structure**

* ReaderView.vue: The container.  
* WordDisplay.vue: The "dumb" component that handles the ORP CSS alignment.  
* Controls.vue: The UI overlay (hidden when mouse is inactive for 2s).

## **7\. Implementation Roadmap for LLM**

1. **Step 1: Backend Core.** Set up FastAPI. Create the TokenizerService class that turns a string into the JSON payload described in Section 3.2.  
2. **Step 2: Frontend Scaffold.** Initialize Vue+Vite. Create the store (Pinia) to hold the word list.  
3. **Step 3: The Engine.** Implement the delta-time loop in Vue to iterate through the word list at a fixed speed.  
4. **Step 4: Alignment.** Implement the CSS logic to align words based on the orp\_index.  
5. **Step 5: File Handling.** Connect the Python file upload endpoint to the Frontend.

## **8\. Definition of Done**

The project is functional when:

1. A user uploads a .md file.  
2. The screen turns black.  
3. Words appear one by one, aligned at the optical center.  
4. The rhythm feels natural (pausing at sentences).  
5. Pressing Space stops the stream instantly.