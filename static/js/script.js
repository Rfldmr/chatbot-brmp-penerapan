document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const chatContainer = document.getElementById('chat-container');
    const resetButton = document.getElementById('reset-chat');
    
    // Fungsi untuk memuat pesan dari server
    function loadMessages() {
        fetch('/api/messages')
            .then(response => response.json())
            .then(data => {
                chatMessages.innerHTML = '';
                data.messages.forEach(message => {
                    addMessageToChat(message.role, message.content);
                });
                scrollToBottom();
            })
            .catch(error => {
                console.error('Error loading messages:', error);
                addMessageToChat('assistant', 'Hai! Ada yang bisa aku bantu hari ini?');
            });
    }
    
    // Fungsi untuk menambahkan pesan ke chat
    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role === 'user' ? 'user-message' : 'assistant-message');
        
        const icon = role === 'user' ? '' : '<i class="fas fa-robot me-2"></i>';
        const bgClass = role === 'user' ? 'bg-primary' : 'bg-light border';
        const textClass = role === 'user' ? 'text-white' : 'text-dark';
        const alignClass = role === 'user' ? 'justify-content-end' : 'justify-content-start';
        
        messageDiv.innerHTML = `
            <div class="d-flex ${alignClass} mb-2">
                <div class="message-bubble ${bgClass} ${textClass} p-3 rounded">
                    <div class="d-flex align-items-center">
                        ${role === 'assistant' ? icon : ''}
                        <div>${content}</div>
                        ${role === 'user' ? icon : ''}
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Fungsi untuk scroll ke bawah
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Fungsi untuk mengirim pesan
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Tambahkan pesan user ke chat
        addMessageToChat('user', message);
        userInput.value = '';
        
        // Tampilkan indikator typing
        const typingIndicator = document.createElement('div');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.innerHTML = `
            <div class="d-flex justify-content-start mb-2">
                <div class="message-bubble bg-light p-3 rounded">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-robot me-2"></i>
                        <div class="typing-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(typingIndicator);
        scrollToBottom();
        
        // Kirim pesan ke server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            // Hapus indikator typing
            const typingElement = document.getElementById('typing-indicator');
            if (typingElement) {
                typingElement.remove();
            }
            
            // Tambahkan respons ke chat
            addMessageToChat('assistant', data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            const typingElement = document.getElementById('typing-indicator');
            if (typingElement) {
                typingElement.remove();
            }
            addMessageToChat('assistant', 'Maaf, terjadi kesalahan. Silakan coba lagi.');
        });
    }
    
    // Event listener untuk form
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });
    
    // Event listener untuk reset chat
    resetButton.addEventListener('click', function() {
        // Langsung jalankan reset tanpa konfirmasi
        fetch('/api/reset', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            chatMessages.innerHTML = '';
            data.messages.forEach(message => {
                addMessageToChat(message.role, message.content);
            });
        })
        .catch(error => {
            console.error('Error resetting chat:', error);
        });
    });
    
    // Muat pesan saat halaman dimuat
    loadMessages();
    
    // Fokus ke input text
    userInput.focus();
    
    // Enter untuk submit
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});