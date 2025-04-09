// static/chat.js (Completo e Corrigido)

// IIFE para encapsular o código e evitar poluir o escopo global
(function() {
    'use strict'; // Habilita modo estrito para pegar erros comuns

    // Cache de elementos DOM frequentemente usados
    let chatBox, messageInput, messageForm, sendBtn, claraStatusElement,
        profilePic, modal, modalImg, closeModalBtn,
        emojiBtn, emojiPicker;

    // --- INICIALIZAÇÃO ---
    function init() {
        // Seleciona os elementos DOM essenciais uma vez
        chatBox = document.getElementById("chat-box");
        messageInput = document.getElementById("mensagem");
        messageForm = document.getElementById("mensagem-form");
        sendBtn = document.querySelector('.send-btn');
        claraStatusElement = document.getElementById("clara-status");
        profilePic = document.getElementById("profile-pic");
        modal = document.getElementById("modal");
        modalImg = document.getElementById("modal-img");
        closeModalBtn = document.querySelector(".modal .close");
        emojiBtn = document.querySelector('.emoji-btn');

        // Verifica se os elementos essenciais do formulário/chat existem
        if (!chatBox || !messageInput || !messageForm || !sendBtn || !claraStatusElement) {
             console.error("Erro: Elementos essenciais do chat não foram encontrados no DOM.");
             return; // Interrompe a inicialização se algo crítico faltar
        }

        // Adiciona listeners do formulário e input
        messageForm.addEventListener("submit", sendMessage);
        messageInput.addEventListener("input", updateSendButton);
        messageInput.addEventListener("keypress", handleEnterKey);
        updateSendButton(); // Define o estado inicial do botão (microfone)

        // Adiciona listener para o botão de emoji (SE ele existir)
        if (emojiBtn) {
            emojiBtn.addEventListener('click', toggleEmojiPicker);
        } else {
            console.warn("Botão de emoji (.emoji-btn) não encontrado.");
        }

        // Adiciona listeners do modal de perfil (se existir)
        if (profilePic && modal && modalImg && closeModalBtn) {
             profilePic.addEventListener("click", openProfileModal);
             closeModalBtn.addEventListener("click", closeProfileModal);
             // Fecha modal se clicar no fundo escuro
             modal.addEventListener("click", function(event) {
                 if (event.target === modal) {
                     closeProfileModal();
                 }
             });
        } else {
             console.warn("Elementos do modal não encontrados. Funcionalidade de clique na foto desativada.");
        }

        // Ajustes de layout na inicialização e em resize
        window.addEventListener('resize', adjustChatHeight);
        adjustChatHeight(); // Ajusta altura inicial

        // Foco inicial no input (bom para desktop)
        messageInput.focus();
    }

    // --- FUNÇÕES DE UTILIDADE ---

    // Gera ou recupera um ID de usuário único (localStorage)
    function getUserId() {
        let userId = localStorage.getItem('user_id');
        if (!userId) {
            userId = 'user-' + Date.now().toString(36) + Math.random().toString(36).substring(2, 7);
            try {
                localStorage.setItem('user_id', userId);
            } catch (e) {
                console.error("Não foi possível salvar user_id no localStorage:", e);
                return 'user-temp-' + Date.now().toString(36);
            }
        }
        return userId;
    }

    // Formata a hora atual para HH:MM (formato 24h)
    function formatTime(date = new Date()) {
        try {
            return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false });
        } catch (e) {
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${hours}:${minutes}`;
        }
    }

    // Rola a área de chat para a última mensagem
    function scrollToBottom() {
        if (chatBox) {
            chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'auto' });
        }
    }

    // Atualiza o status da Clara (online/digitando)
    function setTypingStatus(isTyping) {
        if (claraStatusElement) {
            claraStatusElement.classList.toggle('typing', isTyping);
            claraStatusElement.textContent = isTyping ? "digitando..." : "online";
        }
    }

    // Atualiza o ícone do botão Enviar/Microfone
    function updateSendButton() {
        if (!sendBtn || !messageInput) return;

        if (messageInput.value.trim().length > 0) {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>'; // Ícone Enviar
        } else {
            sendBtn.innerHTML = '<i class="fas fa-microphone"></i>'; // Ícone Microfone
        }
    }

    // Ajusta a altura da área de chat dinamicamente
    function adjustChatHeight() {
        const header = document.querySelector('header');
        const inputContainer = document.querySelector('.input-container');

        if (header && inputContainer && chatBox) {
            const headerHeight = header.offsetHeight;
            const inputHeight = inputContainer.offsetHeight;
            // Subtrai as alturas do header e input da altura total da viewport
            chatBox.style.height = `calc(100vh - ${headerHeight}px - ${inputHeight}px)`;
        }
    }

    // --- LÓGICA PRINCIPAL DO CHAT ---

    // Exibe uma mensagem na tela (usuário ou Clara)
    function displayMessage(message) {
        if (!chatBox || !message.text) return;

        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${message.from}`; // Classe 'me' ou 'her'

        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";
        contentDiv.textContent = message.text; // Define o texto da mensagem
        contentDiv.style.whiteSpace = 'pre-wrap'; // Preserva espaços e quebras de linha
        contentDiv.style.wordBreak = 'break-word'; // Quebra palavras longas
        msgDiv.appendChild(contentDiv);

        const footerDiv = document.createElement("div");
        footerDiv.className = "message-footer";

        const timeSpan = document.createElement("span");
        timeSpan.className = "timestamp";
        timeSpan.textContent = formatTime(); // Pega a hora atual formatada
        footerDiv.appendChild(timeSpan);

        // Adiciona checkmarks apenas para mensagens do usuário ('me')
        if (message.from === "me") {
            const checkSpan = document.createElement("span");
            checkSpan.className = "checkmarks";
            checkSpan.innerHTML = '<i class="fas fa-check"></i>'; // Check simples inicial
            footerDiv.appendChild(checkSpan);

            // Simula o duplo check azul (lido) após um tempo
            const checkmarkSpanForTimeout = checkSpan; // Guarda referência
            setTimeout(() => {
                // Verifica se a mensagem ainda existe no DOM antes de mudar
                if (checkmarkSpanForTimeout && chatBox.contains(checkmarkSpanForTimeout)) {
                    checkmarkSpanForTimeout.innerHTML = '<i class="fas fa-check-double"></i>'; // Check duplo
                    checkmarkSpanForTimeout.classList.add('read'); // Adiciona classe para cor azul (via CSS)
                }
            }, 1500 + Math.random() * 1000); // Tempo aleatório entre 1.5 e 2.5 segundos
        }

        msgDiv.appendChild(footerDiv); // Adiciona rodapé (hora/checks) à mensagem
        chatBox.appendChild(msgDiv); // Adiciona mensagem completa ao chatbox
        scrollToBottom(); // Rola para a nova mensagem
    }

    // Função assíncrona para enviar a mensagem para o backend
    async function sendMessage(event) {
        if (event) event.preventDefault(); // Previne recarregamento da página se for submit de form
        if (!messageInput) return;

        const messageText = messageInput.value.trim(); // Pega texto e remove espaços extras
        if (messageText === "") return; // Não envia mensagem vazia

        const currentUserId = getUserId(); // Pega ou gera ID do usuário

        // Exibe a mensagem do usuário na tela imediatamente
        displayMessage({ from: "me", text: messageText });

        // Limpa o campo de input, atualiza botão para microfone, remove foco do teclado (mobile)
        messageInput.value = "";
        updateSendButton();
        messageInput.blur();

        setTypingStatus(true); // Mostra "digitando..."

        try {
            // ***** LINHA PRINCIPAL DA COMUNICAÇÃO COM BACKEND *****
            // Faz a requisição POST para a rota /chat do Flask
            const response = await fetch("/chat", { // <-- URL CORRIGIDA AQUI
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                // Envia a mensagem no corpo da requisição como JSON
                // Usando 'mensagem' como chave para ser compatível com app.py
                body: JSON.stringify({ mensagem: messageText, user_id: currentUserId })
            });

            // Verifica se a resposta do servidor foi bem sucedida (status 2xx)
            if (!response.ok) {
                let errorDetail = response.statusText; // Pega texto do erro (ex: "Not Found")
                try { // Tenta pegar mais detalhes do corpo da resposta JSON, se houver
                    const errorData = await response.json();
                    errorDetail = errorData.error || errorData.message || errorDetail;
                } catch (e) { /* Ignora se não conseguir ler corpo como JSON */ }
                throw new Error(`Erro ${response.status}: ${errorDetail}`); // Lança um erro
            }

            // Se a resposta foi OK, lê o corpo como JSON
            const data = await response.json();

            // Exibe a resposta da IA (ou uma mensagem padrão se a chave 'resposta' não existir)
            displayMessage({
                from: "her", // Define que a mensagem é da "Dra. Ana"
                text: data.response || "Hmm, não entendi bem o que dizer agora." // Usa 'response' como chave
            });

        } catch (error) {
            // Se houve erro na comunicação (rede, servidor não respondeu, etc.)
            console.error("Falha na comunicação com a API:", error);
            // Mostra uma mensagem de erro no chat para o usuário
            displayMessage({
                from: "her",
                text: `⚠️ Ops! ${error.message || "Tive um problema para me conectar."}`
            });
        } finally {
            // Independentemente de sucesso ou erro, para de mostrar "digitando..."
            setTypingStatus(false);
        }
    }

    // --- Funções do Emoji Picker ---
    function toggleEmojiPicker() {
        if (!emojiPicker) {
            console.log("Criando emoji picker...");
            // Cria o elemento customizado <emoji-picker>
            emojiPicker = document.createElement('emoji-picker');
            // Estilização básica para posicionamento (pode precisar de ajustes)
            emojiPicker.style.position = 'absolute';
            emojiPicker.style.bottom = '60px'; // Ajustar conforme altura do input area
            emojiPicker.style.left = '10px';
            emojiPicker.style.zIndex = '1100'; // Garante que fique sobre outros elementos
            emojiPicker.classList.add('light'); // Tema claro

            document.body.appendChild(emojiPicker); // Adiciona ao DOM

            // Ouve o evento 'emoji-click' disparado pelo componente
            emojiPicker.addEventListener('emoji-click', handleEmojiSelection);

            // Adiciona um listener para fechar se clicar fora (com pequeno delay)
             setTimeout(() => {
                 document.addEventListener('click', handleClickOutsidePicker, { capture: true, once: true });
             }, 0);

        } else {
            console.log("Fechando emoji picker...");
            closeEmojiPicker(); // Se já existe, fecha
        }
    }

    function closeEmojiPicker() {
         if (emojiPicker) {
             emojiPicker.removeEventListener('emoji-click', handleEmojiSelection);
             if (document.body.contains(emojiPicker)) { // Verifica se ainda está no DOM
                  document.body.removeChild(emojiPicker); // Remove do DOM
             }
             emojiPicker = null; // Limpa a variável
             // Remove o listener de clique fora, se ainda existir
              document.removeEventListener('click', handleClickOutsidePicker, { capture: true });
              console.log("Emoji picker fechado.");
         }
    }

    function handleEmojiSelection(event) {
        console.log("Emoji selecionado:", event.detail);
        if (!messageInput) return;

        const emoji = event.detail.unicode; // Pega o caractere emoji
        const cursorPos = messageInput.selectionStart; // Posição atual do cursor

        // Insere o emoji na posição do cursor
        const textBefore = messageInput.value.substring(0, cursorPos);
        const textAfter = messageInput.value.substring(cursorPos);
        messageInput.value = textBefore + emoji + textAfter;

        // Reposiciona o cursor após o emoji inserido
        const newCursorPos = cursorPos + emoji.length;
        messageInput.selectionStart = newCursorPos;
        messageInput.selectionEnd = newCursorPos;

        messageInput.focus(); // Devolve o foco ao input
        updateSendButton(); // Atualiza botão (caso estivesse vazio antes)

        // Opcional: fechar o picker após selecionar um emoji
        // closeEmojiPicker();
    }

    function handleClickOutsidePicker(event) {
        // Fecha se clicou FORA do picker E FORA do botão que o abre
        if (emojiPicker && !emojiPicker.contains(event.target) && emojiBtn && !emojiBtn.contains(event.target)) {
             console.log("Clique fora detectado, fechando picker.");
             closeEmojiPicker();
        } else if (emojiPicker) {
            // Se clicou dentro ou no botão, não fecha e re-adiciona o listener para o próximo clique
             document.addEventListener('click', handleClickOutsidePicker, { capture: true, once: true });
        }
    }
    // --- Fim das Funções do Emoji Picker ---


    // --- Handlers de Eventos Adicionais ---
    function handleEnterKey(event) {
        // Envia mensagem se Enter for pressionado (e Shift não estiver pressionado)
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Previne quebra de linha no input
            if (messageForm) {
                // Dispara o evento 'submit' do formulário (que chama sendMessage)
                messageForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }
    }

    function openProfileModal() {
        // Mostra o modal com a imagem de perfil
        if (modal && modalImg && profilePic) {
            modalImg.src = profilePic.src; // Define a imagem do modal
            modal.style.display = "flex"; // Mostra o modal
        }
    }

    function closeProfileModal() {
        // Esconde o modal
        if (modal) {
            modal.style.display = "none";
        }
    }

    // --- INICIALIZAÇÃO DO SCRIPT ---
    // Espera o DOM carregar completamente antes de rodar o init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init(); // Se já carregou, roda imediatamente
    }

})(); // Fim da IIFE
