(function () {
    "use strict";

    const translations = {
        "Home": "హోమ్",
        "Explore Issues": "సమస్యలను చూడండి",
        "Report an Issue": "సమస్యను నివేదించండి",
        "Issue Map": "సమస్యల మ్యాప్",
        "My Reports": "నా నివేదికలు",
        "Admin Portal": "అడ్మిన్ పోర్టల్",
        "Admin Dashboard": "అడ్మిన్ డాష్‌బోర్డ్",
        "Login": "లాగిన్",
        "Logout": "లాగ్ అవుట్",
        "Sign Up": "నమోదు చేసుకోండి",
        "Create Account": "ఖాతా సృష్టించండి",
        "View Details": "వివరాలు చూడండి",
        "View Details →": "వివరాలు చూడండి →",
        "View Details → ": "వివరాలు చూడండి → ",
        "Report an Issue →": "సమస్యను నివేదించండి →",
        "Get Started": "ప్రారంభించండి",
        "Search": "వెతకండి",
        "Filter": "వడపోత",
        "Status": "స్థితి",
        "Current status:": "ప్రస్తుత స్థితి:",
        "Reported": "నివేదించబడింది",
        "In Progress": "పని జరుగుతోంది",
        "Resolved": "పరిష్కరించబడింది",
        "Roads": "రోడ్లు",
        "Garbage": "చెత్త",
        "Water": "నీరు",
        "Streetlights": "వీధి దీపాలు",
        "Drainage": "మురుగు కాలువలు",
        "Other": "ఇతర",
        "Category:": "వర్గం:",
        "Category": "వర్గం",
        "Locality:": "ప్రాంతం:",
        "Locality": "ప్రాంతం",
        "Priority:": "ప్రాధాన్యత:",
        "Priority": "ప్రాధాన్యత",
        "Date Reported": "నివేదించిన తేదీ",
        "Reported on:": "నివేదించిన తేదీ:",
        "Description": "వివరణ",
        "Title": "శీర్షిక",
        "Name": "పేరు",
        "Email": "ఈమెయిల్",
        "Password": "పాస్‌వర్డ్",
        "Confirm Password": "పాస్‌వర్డ్ నిర్ధారించండి",
        "Submit": "సమర్పించండి",
        "Save Update": "మార్పును సేవ్ చేయండి",
        "Update Status": "స్థితిని మార్చండి",
        "Update Comment": "మార్పు గురించి వ్యాఖ్య",
        "Support This Issue": "ఈ సమస్యకు మద్దతు ఇవ్వండి",
        "Upvote This Issue": "ఈ సమస్యకు ఓటు వేయండి",
        "Status Tracking": "స్థితి వివరాలు",
        "Issue Delayed": "సమస్య ఆలస్యమైంది",
        "No reports yet": "ఇంకా నివేదికలు లేవు",
        "Report #": "నివేదిక సంఖ్య ",
        "Read Aloud": "చదివి వినిపించండి",
        "Stop Reading": "చదవడం ఆపండి",
        "Language": "భాష",
        "English": "ఇంగ్లీష్",
        "Telugu": "తెలుగు",
        "Larger Text": "పెద్ద అక్షరాలు",
        "Smaller Text": "చిన్న అక్షరాలు",
        "Accessibility tools": "సులభంగా ఉపయోగించడానికి",
        "Delayed: unresolved for more than 48 hours.": "హెచ్చరిక: ఈ సమస్య 48 గంటలకుపైగా పరిష్కారం కాలేదు.",
        "⚠️ Delayed: unresolved for more than 48 hours.": "⚠️ హెచ్చరిక: ఈ సమస్య 48 గంటలకుపైగా పరిష్కారం కాలేదు.",
        "This issue has remained unresolved for more than": "ఈ సమస్య ఇంకా పరిష్కారం కాలేదు. గడువు:",
        "48 hours (2 days). Please check the latest progress updates.": "48 గంటలు (2 రోజులు). దయచేసి తాజా వివరాలను చూడండి."
    };

    let fontScale = 1;
    let currentLanguage = "en";
    let originalTextNodes = [];

    function translatePage(language) {
        currentLanguage = language;
        document.documentElement.lang = language === "te" ? "te" : "en";
        if (!originalTextNodes.length) {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                if (node.parentElement && !node.parentElement.closest("#civiclens-accessibility")) {
                    originalTextNodes.push({ node: node, original: node.nodeValue });
                }
            }
        }

        originalTextNodes.forEach(function (entry) {
            let value = entry.original;
            if (language === "te") {
                Object.keys(translations).sort((a, b) => b.length - a.length).forEach(function (english) {
                    value = value.split(english).join(translations[english]);
                });
            }
            entry.node.nodeValue = value;
        });

        document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach(function (element) {
            if (!element.dataset.originalPlaceholder) {
                element.dataset.originalPlaceholder = element.placeholder;
            }
            element.placeholder = language === "te"
                ? (translations[element.dataset.originalPlaceholder] || element.dataset.originalPlaceholder)
                : element.dataset.originalPlaceholder;
        });

        const readButton = document.getElementById("civiclens-read");
        const stopButton = document.getElementById("civiclens-stop");
        if (readButton) readButton.textContent = language === "te" ? "🔊 చదివి వినిపించండి" : "🔊 Read Aloud";
        if (stopButton) stopButton.textContent = language === "te" ? "⏹ చదవడం ఆపండి" : "⏹ Stop Reading";
        document.getElementById("civiclens-language-label").textContent =
            language === "te" ? "భాష / Language" : "Language / భాష";
        document.getElementById("civiclens-larger").textContent =
            language === "te" ? "A+ పెద్ద అక్షరాలు" : "A+ Larger Text";
        document.getElementById("civiclens-smaller").textContent =
            language === "te" ? "A− చిన్న అక్షరాలు" : "A− Smaller Text";
    }

    function buildToolbar() {
        if (document.getElementById("civiclens-accessibility")) return;
        const toolbar = document.createElement("section");
        toolbar.id = "civiclens-accessibility";
        toolbar.className = "civiclens-accessibility";
        toolbar.setAttribute("aria-label", "Accessibility tools");
        toolbar.innerHTML = `
            <label id="civiclens-language-label" for="civiclens-language">Language / భాష</label>
            <select id="civiclens-language" aria-label="Choose language">
                <option value="en">English</option>
                <option value="te">తెలుగు (Telugu)</option>
            </select>
            <button type="button" id="civiclens-larger">A+ Larger Text</button>
            <button type="button" id="civiclens-smaller">A− Smaller Text</button>
            <button type="button" id="civiclens-read">🔊 Read Aloud</button>
            <button type="button" id="civiclens-stop">⏹ Stop Reading</button>`;
        document.body.prepend(toolbar);

        const selector = document.getElementById("civiclens-language");
        let savedLanguage = "en";
        try { savedLanguage = localStorage.getItem("civiclens-language") || "en"; } catch (e) {}
        selector.value = savedLanguage;
        selector.addEventListener("change", function () {
            translatePage(selector.value);
            try { localStorage.setItem("civiclens-language", selector.value); } catch (e) {}
        });

        document.getElementById("civiclens-larger").addEventListener("click", function () {
            fontScale = Math.min(fontScale + 0.1, 1.6);
            document.documentElement.style.setProperty("--civiclens-font-scale", fontScale);
            document.body.classList.add("civiclens-large-text");
        });
        document.getElementById("civiclens-smaller").addEventListener("click", function () {
            fontScale = Math.max(fontScale - 0.1, 0.8);
            document.documentElement.style.setProperty("--civiclens-font-scale", fontScale);
        });
        document.getElementById("civiclens-read").addEventListener("click", function () {
            if (!("speechSynthesis" in window)) {
                alert(currentLanguage === "te"
                    ? "మీ బ్రౌజర్‌లో చదివి వినిపించే సౌకర్యం అందుబాటులో లేదు."
                    : "Text-to-speech is not supported by this browser.");
                return;
            }

            // Cancel any previous speech before starting a new reading.
            window.speechSynthesis.cancel();

            const content = document.querySelector("main") || document.body;
            const clone = content.cloneNode(true);
            clone.querySelectorAll("button, input, select, textarea, script, style, nav").forEach(el => el.remove());
            const spokenText = (clone.innerText || clone.textContent || "")
                .replace(/\s+/g, " ")
                .trim();

            if (!spokenText) return;

            const languageCode = currentLanguage === "te" ? "te-IN" : "en-IN";
            const voices = window.speechSynthesis.getVoices();
            const utterance = new SpeechSynthesisUtterance(spokenText);
            utterance.lang = languageCode;
            // A slightly slower pace and natural pitch make the page easier to follow.
            utterance.rate = currentLanguage === "te" ? 0.78 : 0.88;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            // Select a voice that matches the chosen language instead of relying on
            // the computer's default (which is often English).
            const matchingVoice = currentLanguage === "te"
                ? voices.find(voice => voice.lang.toLowerCase() === "te-in")
                    || voices.find(voice => voice.lang.toLowerCase().startsWith("te-"))
                    || voices.find(voice => voice.lang.toLowerCase() === "te")
                : voices.find(voice => voice.lang.toLowerCase() === "en-in")
                    || voices.find(voice => voice.lang.toLowerCase().startsWith("en-in"))
                    || voices.find(voice => voice.lang.toLowerCase().startsWith("en-"));

            if (matchingVoice) {
                utterance.voice = matchingVoice;
            } else if (currentLanguage === "te") {
                alert("Telugu voice is not installed or available in this browser. On Windows, open Settings → Time & language → Speech, add/install a Telugu speech voice if available, then restart Chrome. You can also try Microsoft Edge, which may provide additional voices.");
                // Do not read Telugu text using an unrelated English voice.
                return;
            }

            window.speechSynthesis.speak(utterance);
        });
        document.getElementById("civiclens-stop").addEventListener("click", function () {
            if ("speechSynthesis" in window) window.speechSynthesis.cancel();
        });
        translatePage(savedLanguage);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", buildToolbar);
    } else {
        buildToolbar();
    }
})();
