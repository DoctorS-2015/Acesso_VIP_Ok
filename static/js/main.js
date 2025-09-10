/**
 * @fileoverview Biblioteca de utilitários e gerenciamento de interface para a aplicação.
 *
 * Este arquivo contém uma coleção de módulos reutilizáveis para:
 * - Funções utilitárias (debounce, formatação, validação).
 * - Sistema de notificações (Toast).
 * - Validador de formulários genérico.
 * - Gerenciador de estado de carregamento para elementos interativos.
 * - Gerenciador de modais.
 * - Controle de atualização automática de páginas.
 * - Orquestrador principal de eventos da aplicação (EventManager).
 */

// --- Configurações Globais ---

/** Objeto de configuração para constantes utilizadas em toda a aplicação. */
const CONFIG = {
    /** Duração padrão (em ms) para a exibição de notificações toast. */
    TOAST_DURATION: 5000,
    /** Duração padrão (em ms) para animações de UI. */
    ANIMATION_DURATION: 300,
    /** Atraso padrão (em ms) para funções com debounce. */
    DEBOUNCE_DELAY: 300,
    /** Intervalo padrão (em ms) para a funcionalidade de auto-refresh. */
    AUTO_REFRESH_INTERVAL: 30000
};

// --- Módulos Utilitários ---

/**
 * @namespace Utils
 * @description Coleção de funções auxiliares de propósito geral.
 */
const Utils = {
    /**
     * Cria uma versão "debounced" de uma função, que atrasa sua execução
     * até que um certo tempo tenha passado sem que ela seja chamada.
     * @param {Function} func - A função a ser executada após o tempo de espera.
     * @param {number} wait - O tempo de espera em milissegundos.
     * @returns {Function} A nova função com debounce.
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Formata um objeto Date ou uma string de data para o padrão brasileiro (dd/mm/aaaa HH:MM).
     * @param {string|Date} date - A data a ser formatada.
     * @returns {string} A data formatada ou uma string vazia se a entrada for inválida.
     */
    formatDate: function(date) {
        if (!date) return '';
        const d = new Date(date);
        return d.toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },

    /**
     * Aplica a máscara de CPF (###.###.###-##) a uma string.
     * @param {string} cpf - O CPF sem formatação.
     * @returns {string} O CPF formatado.
     */
    formatCPF: function(cpf) {
        if (!cpf) return '';
        return cpf.replace(/\D/g, '')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    },

    /**
     * Valida um número de CPF brasileiro.
     * @param {string} cpf - O CPF a ser validado, com ou sem máscara.
     * @returns {boolean} `true` se o CPF for válido, `false` caso contrário.
     */
    validateCPF: function(cpf) {
        cpf = cpf.replace(/\D/g, '');
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

        let sum = 0, remainder;
        for (let i = 1; i <= 9; i++) sum += parseInt(cpf.substring(i - 1, i)) * (11 - i);
        remainder = (sum * 10) % 11;
        if ((remainder === 10) || (remainder === 11)) remainder = 0;
        if (remainder !== parseInt(cpf.substring(9, 10))) return false;

        sum = 0;
        for (let i = 1; i <= 10; i++) sum += parseInt(cpf.substring(i - 1, i)) * (12 - i);
        remainder = (sum * 10) % 11;
        if ((remainder === 10) || (remainder === 11)) remainder = 0;
        if (remainder !== parseInt(cpf.substring(10, 11))) return false;
        return true;
    },

    /**
     * Valida o formato de um endereço de e-mail.
     * @param {string} email - O e-mail a ser validado.
     * @returns {boolean} `true` se o e-mail tiver um formato válido.
     */
    validateEmail: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    /**
     * Gera um ID aleatório simples.
     * @returns {string} Um ID alfanumérico.
     */
    generateId: function() {
        return Math.random().toString(36).substr(2, 9);
    },

    /**
     * Rola a página suavemente até um elemento específico.
     * @param {HTMLElement} element - O elemento de destino.
     * @param {number} [offset=0] - Um deslocamento vertical em pixels.
     */
    scrollTo: function(element, offset = 0) {
        const targetPosition = element.offsetTop - offset;
        window.scrollTo({ top: targetPosition, behavior: 'smooth' });
    },

    /**
     * Verifica se um elemento está totalmente visível na janela de visualização.
     * @param {HTMLElement} element - O elemento a ser verificado.
     * @returns {boolean} `true` se o elemento estiver visível.
     */
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 && rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

/**
 * @namespace Toast
 * @description Sistema para exibir notificações não-bloqueantes (toasts).
 */
const Toast = {
    container: null,

    /**
     * Cria e injeta o contêiner de toasts no DOM, se ainda não existir.
     */
    init: function() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(this.container);
        }
    },

    /**
     * Exibe uma notificação toast.
     * @param {string} message - A mensagem a ser exibida.
     * @param {('info'|'success'|'warning'|'error')} [type='info'] - O tipo de toast.
     * @param {number} [duration=CONFIG.TOAST_DURATION] - Duração em ms para o toast desaparecer.
     * @returns {HTMLElement} O elemento do toast criado.
     */
    show: function(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
        this.init();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} bg-white border border-gray-200 rounded-lg shadow-lg p-4 max-w-sm transform transition-all duration-300 translate-x-full opacity-0`;

        const icon = this.getIcon(type);
        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0"><i class="fas ${icon} text-lg ${this.getIconColor(type)}"></i></div>
                <div class="ml-3"><p class="text-sm font-medium text-gray-900">${message}</p></div>
                <div class="ml-auto pl-3">
                    <button class="toast-close text-gray-400 hover:text-gray-600 transition-colors duration-200"><i class="fas fa-times"></i></button>
                </div>
            </div>`;
        this.container.appendChild(toast);

        // Animação de entrada.
        setTimeout(() => toast.classList.remove('translate-x-full', 'opacity-0'), 10);

        // Agendamento para remoção automática.
        const autoRemove = setTimeout(() => this.remove(toast), duration);

        // Permite fechar o toast manualmente.
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(autoRemove);
            this.remove(toast);
        });
        return toast;
    },

    /**
     * Remove um toast do DOM com uma animação de saída.
     * @param {HTMLElement} toast - O elemento do toast a ser removido.
     */
    remove: function(toast) {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, CONFIG.ANIMATION_DURATION);
    },

    /**
     * Retorna a classe do ícone FontAwesome com base no tipo de toast.
     * @param {string} type - O tipo do toast.
     * @returns {string} A classe do ícone.
     * @private
     */
    getIcon: function(type) {
        const icons = {
            success: 'fa-check-circle', error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle', info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    },

    /**
     * Retorna a classe de cor (TailwindCSS) com base no tipo de toast.
     * @param {string} type - O tipo do toast.
     * @returns {string} A classe de cor.
     * @private
     */
    getIconColor: function(type) {
        const colors = {
            success: 'text-green-500', error: 'text-red-500',
            warning: 'text-yellow-500', info: 'text-blue-500'
        };
        return colors[type] || colors.info;
    },

    /** Atalhos para os tipos de toast mais comuns. */
    success: function(message, duration) { return this.show(message, 'success', duration); },
    error: function(message, duration) { return this.show(message, 'error', duration); },
    warning: function(message, duration) { return this.show(message, 'warning', duration); },
    info: function(message, duration) { return this.show(message, 'info', duration); }
};

/**
 * @namespace FormValidator
 * @description Sistema genérico para validação de formulários com base em atributos de dados.
 */
const FormValidator = {
    /** Regras de validação disponíveis. */
    rules: {
        required: (value) => value.trim() !== '',
        email: (value) => Utils.validateEmail(value),
        cpf: (value) => Utils.validateCPF(value),
        minLength: (value, min) => value.length >= parseInt(min),
        maxLength: (value, max) => value.length <= parseInt(max),
        pattern: (value, pattern) => new RegExp(pattern).test(value)
    },

    /**
     * Valida um formulário inteiro.
     * @param {HTMLFormElement} form - O formulário a ser validado.
     * @returns {Array<Object>} Um array de objetos de erro. Vazio se não houver erros.
     */
    validate: function(form) {
        const errors = [];
        const inputs = form.querySelectorAll('[data-validate]');
        inputs.forEach(input => {
            const rules = input.dataset.validate.split('|');
            const value = input.value;
            const fieldName = input.dataset.fieldName || input.name || 'Campo';

            for (const rule of rules) {
                const [ruleName, ruleValue] = rule.split(':');
                if (this.rules[ruleName]) {
                    const isValid = this.rules[ruleName](value, ruleValue);
                    if (!isValid) {
                        errors.push({
                            field: input,
                            message: this.getErrorMessage(ruleName, fieldName, ruleValue)
                        });
                        break; // Para no primeiro erro do campo
                    }
                }
            }
        });
        return errors;
    },

    /**
     * Obtém a mensagem de erro apropriada para uma regra de validação.
     * @param {string} rule - O nome da regra (ex: 'required').
     * @param {string} fieldName - O nome do campo para a mensagem.
     * @param {string} [value] - O valor associado à regra (ex: para 'minLength').
     * @returns {string} A mensagem de erro formatada.
     * @private
     */
    getErrorMessage: function(rule, fieldName, value) {
        const messages = {
            required: `${fieldName} é obrigatório`,
            email: `${fieldName} deve ser um email válido`,
            cpf: `${fieldName} deve ser um CPF válido`,
            minLength: `${fieldName} deve ter pelo menos ${value} caracteres`,
            maxLength: `${fieldName} deve ter no máximo ${value} caracteres`,
            pattern: `${fieldName} não atende ao formato exigido`
        };
        return messages[rule] || `${fieldName} é inválido`;
    },

    /**
     * Exibe os erros de validação na interface, junto aos campos correspondentes.
     * @param {Array<Object>} errors - O array de erros retornado por `validate`.
     */
    showErrors: function(errors) {
        this.clearErrors();
        errors.forEach(error => {
            error.field.classList.add('border-red-500');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error text-red-500 text-sm mt-1';
            errorDiv.textContent = error.message;
            error.field.parentNode.insertBefore(errorDiv, error.field.nextSibling);
        });
    },

    /**
     * Limpa todos os erros de validação visíveis na página.
     */
    clearErrors: function() {
        document.querySelectorAll('.field-error').forEach(e => e.remove());
        document.querySelectorAll('.border-red-500').forEach(f => f.classList.remove('border-red-500'));
    }
};

/**
 * @namespace LoadingManager
 * @description Controla a exibição de estados de carregamento em botões e outros elementos.
 */
const LoadingManager = {
    /**
     * Ativa o estado de carregamento em um elemento.
     * @param {HTMLElement} element - O elemento (geralmente um botão).
     * @param {string} [text='Carregando...'] - O texto a ser exibido.
     */
    show: function(element, text = 'Carregando...') {
        if (!element) return;
        element.disabled = true;
        element.dataset.originalContent = element.innerHTML;
        element.innerHTML = `<span class="loading-spinner mr-2"></span> ${text}`;
    },

    /**
     * Desativa o estado de carregamento e restaura o conteúdo original do elemento.
     * @param {HTMLElement} element - O elemento.
     */
    hide: function(element) {
        if (!element) return;
        element.disabled = false;
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
    }
};

/**
 * @namespace ModalManager
 * @description Gerencia a abertura e o fechamento de modais.
 */
const ModalManager = {
    /**
     * Abre um modal.
     * @param {string} modalId - O ID do elemento do modal.
     */
    open: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.style.overflow = 'hidden';

            // Armadilha de foco para acessibilidade: foca no primeiro elemento interativo.
            const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusable.length > 0) focusable[0].focus();
        }
    },

    /**
     * Fecha um modal.
     * @param {string} modalId - O ID do elemento do modal.
     */
    close: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.style.overflow = '';
        }
    },

    /**
     * Configura um modal para fechar ao clicar fora de sua área de conteúdo.
     * @param {string} modalId - O ID do elemento do modal.
     */
    closeOnOutsideClick: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.close(modalId);
            });
        }
    }
};

/**
 * @namespace AutoRefresh
 * @description Gerencia a funcionalidade de atualização automática de página.
 */
const AutoRefresh = {
    intervals: new Map(),

    /**
     * Inicia um novo intervalo de atualização automática.
     * @param {Function} callback - A função a ser chamada a cada intervalo.
     * @param {number} [interval=CONFIG.AUTO_REFRESH_INTERVAL] - O intervalo em ms.
     * @returns {string} O ID único do intervalo, para posterior cancelamento.
     */
    start: function(callback, interval = CONFIG.AUTO_REFRESH_INTERVAL) {
        const id = Utils.generateId();
        this.intervals.set(id, setInterval(callback, interval));
        return id;
    },

    /**
     * Para um intervalo de atualização específico.
     * @param {string} id - O ID do intervalo retornado por `start`.
     */
    stop: function(id) {
        if (this.intervals.has(id)) {
            clearInterval(this.intervals.get(id));
            this.intervals.delete(id);
        }
    },

    /**
     * Para todos os intervalos de atualização ativos.
     */
    stopAll: function() {
        this.intervals.forEach(clearInterval);
        this.intervals.clear();
    }
};

/**
 * @namespace EventManager
 * @description Orquestrador de funcionalidades específicas da aplicação.
 */
const EventManager = {
    /**
     * Inicializa as funcionalidades específicas da página.
     */
    init: function() {
        this.setupFormValidation();
        this.setupCPFMask();
        this.setupDateValidation();
        this.setupAutoRefresh();
    },

    /**
     * Anexa o validador a todos os formulários marcados com `data-validate="true"`.
     */
    setupFormValidation: function() {
        document.querySelectorAll('form[data-validate="true"]').forEach(form => {
            form.addEventListener('submit', (e) => {
                const errors = FormValidator.validate(form);
                if (errors.length > 0) {
                    e.preventDefault();
                    FormValidator.showErrors(errors);
                    Toast.error('Por favor, corrija os erros no formulário');
                } else {
                    FormValidator.clearErrors();
                }
            });
        });
    },

    /**
     * Aplica a máscara de CPF a todos os inputs marcados com `data-mask="cpf"`.
     */
    setupCPFMask: function() {
        document.querySelectorAll('input[data-mask="cpf"]').forEach(input => {
            input.addEventListener('input', (e) => e.target.value = Utils.formatCPF(e.target.value));
        });
    },

    /**
     * Adiciona validação de interdependência entre campos de data de início e fim.
     */
    setupDateValidation: function() {
        document.querySelectorAll('input[name="data_inicio"]').forEach(startInput => {
            const form = startInput.closest('form');
            const endInput = form ? form.querySelector('input[name="data_fim"]') : null;
            if (endInput) {
                startInput.addEventListener('change', () => {
                    endInput.min = startInput.value;
                    if (endInput.value && endInput.value < startInput.value) {
                        endInput.value = '';
                        Toast.warning('A data de término deve ser posterior à data de início.');
                    }
                });
            }
        });
    },

    /**
     * Configura a atualização automática para páginas de relatório.
     */
    setupAutoRefresh: function() {
        if (window.location.pathname.includes('relatorio')) {
            // Apenas atualiza automaticamente se não houver filtros aplicados na URL.
            const urlParams = new URLSearchParams(window.location.search);
            if (!urlParams.has('status') && !urlParams.has('data_inicio') && !urlParams.has('data_fim')) {
                AutoRefresh.start(() => window.location.reload());
            }
        }
    },

    /**
     * Exibe um diálogo de confirmação padrão do navegador antes de executar uma ação.
     * @param {string} message - A mensagem de confirmação.
     * @param {Function} callback - A função a ser executada se o usuário confirmar.
     */
    confirmAction: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },

    /**
     * Gerencia o estado de carregamento do botão de submissão de um formulário.
     * @param {HTMLFormElement} form - O formulário.
     * @param {string} [loadingText='Processando...'] - Texto do estado de carregamento.
     */
    handleFormSubmit: function(form, loadingText = 'Processando...') {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            form.addEventListener('submit', () => {
                // Apenas mostra o loading se o formulário for válido.
                if (FormValidator.validate(form).length === 0) {
                    LoadingManager.show(submitButton, loadingText);
                    // Fallback para reativar o botão caso algo dê errado.
                    setTimeout(() => LoadingManager.hide(submitButton), 10000);
                }
            });
        }
    }
};


// --- Inicialização da Aplicação ---

/**
 * Ponto de entrada principal do script após o carregamento completo do DOM.
 */
document.addEventListener('DOMContentLoaded', function() {
    Toast.init();
    EventManager.init();

    // Configura listeners globais de teclado.
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal:not(.hidden)').forEach(modal => ModalManager.close(modal.id));
        }
    });

    // Configura o fechamento de modais ao clicar na área externa.
    document.querySelectorAll('.modal').forEach(modal => ModalManager.closeOnOutsideClick(modal.id));

    // Anexa o gerenciador de estado de carregamento a todos os formulários.
    document.querySelectorAll('form').forEach(form => EventManager.handleFormSubmit(form));

    // Exibe toasts para mensagens de sucesso/erro passadas via parâmetros de URL.
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('success')) Toast.success(decodeURIComponent(urlParams.get('success')));
    if (urlParams.has('error')) Toast.error(decodeURIComponent(urlParams.get('error')));
});

/**
 * Executa tarefas de limpeza antes que o usuário saia da página.
 */
window.addEventListener('beforeunload', function() {
    AutoRefresh.stopAll();
});


// --- Exposição Global ---

/**
 * Expõe módulos ao objeto `window` para acesso global,
 * útil para chamadas a partir do HTML (ex: onclick) ou para depuração.
 */
window.Utils = Utils;
window.Toast = Toast;
window.FormValidator = FormValidator;
window.LoadingManager = LoadingManager;
window.ModalManager = ModalManager;
window.AutoRefresh = AutoRefresh;
window.EventManager = EventManager;