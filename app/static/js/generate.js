// JavaScript for generation page with SSE (Server-Sent Events)

// Load tender preview
function loadTenderPreview() {
    const tenderId = document.getElementById('tender_id').value;
    const preview = document.getElementById('tender-preview');
    const previewText = document.getElementById('tender-text');

    if (!tenderId) {
        preview.style.display = 'none';
        return;
    }

    // Fetch document data
    fetch(`/api/document/${tenderId}`)
        .then(response => response.json())
        .then(data => {
            if (data.extracted_text) {
                previewText.textContent = data.extracted_text;
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading tender preview:', error);
            preview.style.display = 'none';
        });
}

// Analyze tender with SSE
function analyzeTender() {
    const tenderId = document.getElementById('tender_id').value;

    if (!tenderId) {
        alert('Veuillez sélectionner un appel d\'offre');
        return;
    }

    const analyzeBtn = document.getElementById('analyzeBtn');
    const analysisResult = document.getElementById('analysis-result');
    const analysisContent = document.getElementById('analysis-content');

    // Show loading state
    analyzeBtn.classList.add('btn-loading');
    analyzeBtn.disabled = true;
    analysisResult.style.display = 'block';
    analysisContent.innerHTML = '<div class="loading-spinner"></div> Analyse en cours...';

    // Create EventSource for SSE
    const eventSource = new EventSource(`/api/analyze/${tenderId}`);
    let fullAnalysis = '';

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'chunk') {
            fullAnalysis += data.content;
            // Convert markdown to HTML (basic)
            analysisContent.innerHTML = markdownToHtml(fullAnalysis) + '<span class="streaming-cursor"></span>';
        } else if (data.type === 'done') {
            analysisContent.innerHTML = markdownToHtml(fullAnalysis);
            analyzeBtn.classList.remove('btn-loading');
            analyzeBtn.disabled = false;
            eventSource.close();
        } else if (data.type === 'error') {
            analysisContent.innerHTML = `<div class="alert alert-danger">Erreur: ${data.message}</div>`;
            analyzeBtn.classList.remove('btn-loading');
            analyzeBtn.disabled = false;
            eventSource.close();
        }
    };

    eventSource.onerror = function(error) {
        console.error('SSE Error:', error);
        analysisContent.innerHTML = '<div class="alert alert-danger">Erreur de connexion</div>';
        analyzeBtn.classList.remove('btn-loading');
        analyzeBtn.disabled = false;
        eventSource.close();
    };
}

// Handle form submission for quote generation
document.getElementById('generateForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const tenderId = document.getElementById('tender_id').value;

    if (!tenderId) {
        alert('Veuillez sélectionner un appel d\'offre');
        return;
    }

    // Get selected templates
    const templateCheckboxes = document.querySelectorAll('.template-checkbox:checked');
    const templateIds = Array.from(templateCheckboxes).map(cb => parseInt(cb.value));

    // Get additional context
    const additionalContext = document.getElementById('additional_context').value;

    // Show generation result section
    const generationResult = document.getElementById('generation-result');
    const generationStatus = document.getElementById('generation-status');
    const generationContent = document.getElementById('generation-content');
    const downloadSection = document.getElementById('download-section');

    generationResult.style.display = 'block';
    generationStatus.style.display = 'block';
    generationContent.innerHTML = '';
    downloadSection.style.display = 'none';

    // Disable submit button
    const submitBtn = this.querySelector('button[type="submit"]');
    submitBtn.classList.add('btn-loading');
    submitBtn.disabled = true;

    // Scroll to result
    generationResult.scrollIntoView({ behavior: 'smooth' });

    // Create EventSource for SSE
    fetch('/api/generate-quote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tender_id: tenderId,
            template_ids: templateIds,
            additional_context: additionalContext
        })
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = '';

        function processText({ done, value }) {
            if (done) {
                submitBtn.classList.remove('btn-loading');
                submitBtn.disabled = false;
                return;
            }

            // Decode the chunk
            buffer += decoder.decode(value, { stream: true });

            // Split by newlines to process complete messages
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));

                        if (data.type === 'chunk') {
                            fullContent += data.content;
                            generationContent.innerHTML = markdownToHtml(fullContent) + '<span class="streaming-cursor"></span>';
                            generationStatus.innerHTML = `<i class="bi bi-hourglass-split"></i> ${fullContent.length} caractères générés...`;
                        } else if (data.type === 'done') {
                            generationContent.innerHTML = markdownToHtml(fullContent);
                            generationStatus.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle"></i> Offre générée avec succès en ${data.time} secondes!</div>`;

                            // Show download button
                            const downloadBtn = document.getElementById('download-btn');
                            downloadBtn.href = `/download/${data.doc_id}`;
                            downloadSection.style.display = 'block';

                            submitBtn.classList.remove('btn-loading');
                            submitBtn.disabled = false;
                        } else if (data.type === 'error') {
                            generationStatus.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Erreur: ${data.message}</div>`;
                            submitBtn.classList.remove('btn-loading');
                            submitBtn.disabled = false;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            });

            // Continue reading
            return reader.read().then(processText);
        }

        return reader.read().then(processText);
    }).catch(error => {
        console.error('Generation error:', error);
        generationStatus.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Erreur de connexion</div>`;
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
    });
});

// Basic markdown to HTML converter
function markdownToHtml(markdown) {
    let html = markdown;

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph
    html = '<p>' + html + '</p>';

    // Lists (basic)
    html = html.replace(/<p>-\s(.+?)<\/p>/g, '<ul><li>$1</li></ul>');
    html = html.replace(/<\/ul><br><ul>/g, '');

    return html;
}
