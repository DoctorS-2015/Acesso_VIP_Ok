/**
 * @fileoverview Lógica de frontend para a página de validação de acesso.
 * Este script gerencia um formulário de múltiplas etapas, valida os dados do
 * usuário em tempo real, aplica máscaras de input e controla a exibição
 * dos resultados (acesso liberado/negado) em um modal.
 */

// --- Configurações e Constantes ---

/** Lista de nomes considerados VIP para acesso direto à etapa de CPF. */
const VIP_LIST = [
    "Jair Messias Bolsonaro",
    "Luiz Inácio Lula Da Silva",
    "Lula",
    "Carlos Bolsonaro",
    "Emmanuel Macron",
    "Bolsonaro"
];

/** Lista de códigos de ingresso válidos. */
const VALID_TICKETS = [
    "ING123",
    "ING456",
    "ING789"
];

// --- Módulos Principais ---

/**
 * @namespace ValidationSystem
 * @description Objeto principal que encapsula toda a lógica de validação do formulário.
 */
const ValidationSystem = {
    currentStep: 'step-nome',
    formData: {},

    /**
     * Ponto de entrada. Inicializa todos os componentes do sistema de validação.
     */
    init: function() {
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupCPFMask();
        this.setupKeyboardNavigation();
        this.focusFirstInput();
    },

    /**
     * Configura todos os listeners de eventos necessários para a interatividade do formulário.
     */
    setupEventListeners: function() {
        // Listener para o botão de verificação de nome.
        const nomeButton = document.querySelector('#step-nome button');
        if (nomeButton) {
            nomeButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.verificarNome();
            });
        }

        // Listener para o botão de continuar na etapa de ingresso.
        const ingressoButton = document.querySelector('#step-ingresso button');
        if (ingressoButton) {
            ingressoButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.mostrarProximaEtapa('step-cpf');
            });
        }

        // Listener para o evento de submissão final do formulário.
        const form = document.getElementById('validationForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                this.handleFormSubmission(e);
            });
        }

        // Adiciona navegação via tecla "Enter" em todos os inputs.
        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleEnterKey(input);
                }
            });
        });

        // Adiciona validação em tempo real quando o usuário sai de um campo (blur)
        // e limpa o erro quando começa a digitar novamente (input).
        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    },

    /**
     * Configura atributos de dados para habilitar a validação nos campos do formulário.
     */
    setupFormValidation: function() {
        const form = document.getElementById('validationForm');
        if (form) form.setAttribute('data-validate', 'true');

        const nomeInput = document.querySelector('input[name="nome"]');
        if (nomeInput) {
            nomeInput.setAttribute('data-validate', 'required|minLength:2');
            nomeInput.setAttribute('data-field-name', 'Nome');
        }

        const cpfInput = document.querySelector('input[name="cpf"]');
        if (cpfInput) {
            cpfInput.setAttribute('data-validate', 'required|cpf');
            cpfInput.setAttribute('data-field-name', 'CPF');
            cpfInput.setAttribute('data-mask', 'cpf');
        }
    },

    /**
     * Aplica uma máscara de formatação (###.###.###-##) ao campo de CPF.
     */
    setupCPFMask: function() {
        const cpfInput = document.querySelector('input[name="cpf"]');
        if (cpfInput) {
            cpfInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
                e.target.value = value;
            });
        }
    },

    /**
     * Configura atalhos de teclado, como a tecla 'Escape' para reiniciar o formulário.
     */
    setupKeyboardNavigation: function() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.resetForm();
            }
        });
    },

    /**
     * Coloca o foco automaticamente no primeiro campo do formulário ao carregar a página.
     */
    focusFirstInput: function() {
        const firstInput = document.querySelector('#step-nome input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    },

    /**
     * Normaliza uma string, removendo acentos e convertendo para minúsculas.
     * Útil para comparações de texto consistentes.
     * @param {string} str - A string a ser normalizada.
     * @returns {string} A string normalizada.
     */
    normalizeString: function(str) {
        return str.normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    },

    /**
     * Verifica se um nome está na lista VIP.
     * @param {string} nome - O nome a ser verificado.
     * @returns {boolean} Verdadeiro se o nome for VIP.
     */
    isVIP: function(nome) {
        const nomeNormalizado = this.normalizeString(nome);
        return VIP_LIST.some(vip => this.normalizeString(vip) === nomeNormalizado);
    },

    /**
     * Verifica se um código de ingresso é válido.
     * @param {string} ingresso - O código do ingresso.
     * @returns {boolean} Verdadeiro se o ingresso for válido.
     */
    isValidTicket: function(ingresso) {
        return VALID_TICKETS.includes(ingresso.toUpperCase());
    },

    /**
     * Processa a primeira etapa: verifica o nome e decide o próximo passo
     * (CPF para VIPs, Ingresso para não-VIPs).
     */
    verificarNome: function() {
        const nomeInput = document.querySelector('input[name="nome"]');
        const nome = nomeInput.value.trim();

        if (!nome) {
            this.showFieldError(nomeInput, 'Por favor, digite seu nome');
            nomeInput.focus();
            return;
        }

        if (nome.length < 2) {
            this.showFieldError(nomeInput, 'Nome deve ter pelo menos 2 caracteres');
            nomeInput.focus();
            return;
        }

        this.formData.nome = nome;

        if (this.isVIP(nome)) {
            this.showVIPMessage(nome);
            setTimeout(() => this.mostrarProximaEtapa('step-cpf'), 1500);
        } else {
            this.mostrarProximaEtapa('step-ingresso');
        }
    },

    /**
     * Exibe uma notificação (toast) de boas-vindas para usuários VIP.
     * @param {string} nome - O nome do VIP.
     */
    showVIPMessage: function(nome) {
        Toast.success(`Bem-vindo, ${nome}! Você está na lista VIP.`, 2000);
    },

    /**
     * Transita entre as etapas do formulário, mostrando a etapa alvo e ocultando as outras.
     * @param {string} stepId - O ID do elemento da etapa a ser exibida.
     */
    mostrarProximaEtapa: function(stepId) {
        document.querySelectorAll('[id^="step-"]').forEach(step => {
            step.classList.add('hidden');
        });

        const targetStep = document.getElementById(stepId);
        if (targetStep) {
            targetStep.classList.remove('hidden');
            targetStep.classList.add('slide-in');

            // Foca no primeiro input da nova etapa para melhor usabilidade.
            const input = targetStep.querySelector('input');
            if (input) {
                setTimeout(() => input.focus(), 300);
            }
        }
        this.currentStep = stepId;
    },

    /**
     * Exibe a tela de carregamento durante a submissão do formulário.
     */
    mostrarCarregando: function() {
        document.querySelectorAll('[id^="step-"]').forEach(step => {
            step.classList.add('hidden');
        });

        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.remove('hidden');
        }
    },

    /**
     * Lida com a submissão final do formulário, validando a etapa atual antes de enviar.
     * @param {Event} e - O objeto do evento de submissão.
     */
    handleFormSubmission: function(e) {
        const currentStepElement = document.getElementById(this.currentStep);
        const inputs = currentStepElement.querySelectorAll('input');
        let hasErrors = false;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                hasErrors = true;
            }
        });

        if (hasErrors) {
            e.preventDefault();
            Toast.error('Por favor, corrija os erros antes de continuar');
            return;
        }

        this.mostrarCarregando();

        // Armazena os dados finais antes de permitir que o formulário seja enviado.
        inputs.forEach(input => {
            this.formData[input.name] = input.value;
        });

        // Permite que a submissão padrão do formulário (POST) continue.
    },

    /**
     * Valida um campo individual com base no seu nome e regras.
     * @param {HTMLInputElement} input - O elemento de input a ser validado.
     * @returns {boolean} Verdadeiro se o campo for válido.
     */
    validateField: function(input) {
        const value = input.value.trim();
        const name = input.name;
        let isValid = true;
        let errorMessage = '';

        switch (name) {
            case 'nome':
                if (!value) {
                    isValid = false;
                    errorMessage = 'Nome é obrigatório';
                } else if (value.length < 2) {
                    isValid = false;
                    errorMessage = 'Nome deve ter pelo menos 2 caracteres';
                }
                break;
            case 'cpf':
                if (!value) {
                    isValid = false;
                    errorMessage = 'CPF é obrigatório';
                } else if (!Utils.validateCPF(value)) {
                    isValid = false;
                    errorMessage = 'CPF inválido';
                }
                break;
            case 'ingresso':
                // Ingresso é opcional, mas se preenchido, deve ter um formato mínimo.
                if (value && value.length < 3) {
                    isValid = false;
                    errorMessage = 'Código do ingresso parece ser inválido';
                }
                break;
        }

        if (!isValid) {
            this.showFieldError(input, errorMessage);
        } else {
            this.clearFieldError(input);
        }
        return isValid;
    },

    /**
     * Exibe uma mensagem de erro visualmente associada a um campo.
     * @param {HTMLInputElement} input - O campo com erro.
     * @param {string} message - A mensagem de erro a ser exibida.
     */
    showFieldError: function(input, message) {
        this.clearFieldError(input);
        input.classList.add('border-red-500', 'border-2');

        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error text-red-200 text-sm mt-2 animate-fade-in';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>${message}`;

        input.parentNode.appendChild(errorDiv);
    },

    /**
     * Remove a mensagem de erro de um campo.
     * @param {HTMLInputElement} input - O campo a ser limpo.
     */
    clearFieldError: function(input) {
        input.classList.remove('border-red-500', 'border-2');
        const existingError = input.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    },

    /**
     * Simula o clique no botão da etapa atual quando a tecla "Enter" é pressionada.
     * @param {HTMLInputElement} input - O campo onde a tecla foi pressionada.
     */
    handleEnterKey: function(input) {
        const currentStepElement = input.closest('[id^="step-"]');
        const button = currentStepElement.querySelector('button');
        if (button) {
            button.click();
        }
    },

    /**
     * Restaura o formulário ao seu estado inicial.
     */
    resetForm: function() {
        this.formData = {};

        const form = document.getElementById('validationForm');
        if (form) form.reset();

        document.querySelectorAll('.field-error').forEach(error => error.remove());
        document.querySelectorAll('.border-red-500').forEach(input => {
            input.classList.remove('border-red-500', 'border-2');
        });

        this.mostrarProximaEtapa('step-nome');

        const loading = document.getElementById('loading');
        if (loading) loading.classList.add('hidden');
    },

    /**
     * Obtém um resumo da lógica de validação com base nos dados coletados.
     * @returns {object} Um objeto contendo o resumo da validação.
     */
    getValidationSummary: function() {
        const nome = this.formData.nome || '';
        const ingresso = this.formData.ingresso || '';
        const cpf = this.formData.cpf || '';

        const isVIP = this.isVIP(nome);
        const hasValidTicket = this.isValidTicket(ingresso);
        const hasValidCPF = Utils.validateCPF(cpf);

        return {
            nome,
            ingresso,
            cpf,
            isVIP,
            hasValidTicket,
            hasValidCPF,
            shouldAllow: (isVIP || hasValidTicket) && hasValidCPF
        };
    }
};

/**
 * @namespace ResultModal
 * @description Gerencia a exibição e o fechamento do modal de resultado.
 */
const ResultModal = {
    /**
     * Exibe o modal de resultado (liberado ou negado).
     * @param {boolean} isAllowed - Define se o acesso foi liberado.
     * @param {string} [message] - Mensagem customizada para acesso negado.
     */
    show: function(isAllowed, message) {
        const modal = document.getElementById('resultModal');
        if (!modal) return;

        const icon = modal.querySelector('.fas');
        const title = modal.querySelector('h3');
        const description = modal.querySelector('p');
        const iconContainer = icon.parentElement;

        if (isAllowed) {
            iconContainer.className = 'w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4';
            icon.className = 'fas fa-check text-green-500 text-3xl';
            title.textContent = 'Acesso Liberado!';
            title.className = 'text-2xl font-bold text-green-600 mb-2';
            description.textContent = 'Bem-vindo ao evento';
        } else {
            iconContainer.className = 'w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4';
            icon.className = 'fas fa-times text-red-500 text-3xl';
            title.textContent = 'Acesso Negado';
            title.className = 'text-2xl font-bold text-red-600 mb-2';
            description.textContent = message || 'Os dados não conferem com nossa lista de acesso.';
        }

        modal.style.display = 'flex';

        // Para acesso negado, o modal fecha automaticamente após 5 segundos.
        if (!isAllowed) {
            setTimeout(() => this.close(), 5000);
        }
    },

    /**
     * Fecha o modal de resultado e reinicia o formulário.
     */
    close: function() {
        const modal = document.getElementById('resultModal');
        if (modal) {
            modal.style.display = 'none';
            ValidationSystem.resetForm();
        }
    }
};

/**
 * @namespace DebugSystem
 * @description Controla a exibição de informações de depuração da lógica de validação.
 */
const DebugSystem = {
    /**
     * Alterna a visibilidade do painel de detalhes da lógica.
     */
    toggleLogica: function() {
        const div = document.getElementById('logica-detalhes');
        if (div) div.classList.toggle('hidden');
    },

    /**
     * Exibe o resumo da validação no painel de depuração.
     */
    showValidationLogic: function() {
        const summary = ValidationSystem.getValidationSummary();
        const logicDiv = document.getElementById('logica-detalhes');

        if (logicDiv) {
            logicDiv.innerHTML = `
                <div class="text-xs space-y-1">
                    <div>VIP: ${summary.isVIP ? '✓' : '✗'}</div>
                    <div>Ingresso Válido: ${summary.hasValidTicket ? '✓' : '✗'}</div>
                    <div>CPF Válido: ${summary.hasValidCPF ? '✓' : '✗'}</div>
                    <div>Resultado: ${summary.shouldAllow ? 'LIBERADO' : 'NEGADO'}</div>
                </div>
            `;
        }
    }
};

// --- Inicialização da Aplicação ---

document.addEventListener('DOMContentLoaded', function() {
    // Garante que o script de validação só execute na página correta.
    if (document.getElementById('validationForm')) {
        ValidationSystem.init();

        const closeModalBtn = document.querySelector('[onclick="fecharModal()"]');
        if (closeModalBtn) {
            closeModalBtn.onclick = () => ResultModal.close();
        }

        const debugBtn = document.querySelector('[onclick="toggleLogica()"]');
        if (debugBtn) {
            debugBtn.onclick = () => {
                DebugSystem.toggleLogica();
                DebugSystem.showValidationLogic();
            };
        }
    }
});

// --- Exposição Global ---

// Expõe os módulos ao objeto `window` para que possam ser chamados
// por funções `onclick` no HTML ou para depuração no console.
window.ValidationSystem = ValidationSystem;
window.ResultModal = ResultModal;
window.DebugSystem = DebugSystem;