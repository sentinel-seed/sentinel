/**
 * Sentinel Guard - Internationalization (i18n)
 * Supports: English (en), Spanish (es), Portuguese (pt)
 */

export type Language = 'en' | 'es' | 'pt';

export interface Translations {
  // Header
  appName: string;
  protected: string;
  disabled: string;

  // Navigation
  dashboard: string;
  alerts: string;
  settings: string;
  agentMonitor: string;
  approvals: string;
  rules: string;

  // Dashboard
  threatsBlocked: string;
  secretsCaught: string;
  sessionsProtected: string;
  protection: string;
  quickActions: string;
  scanPage: string;
  checkClipboard: string;

  // Protection levels
  protectionLevel: string;
  basic: string;
  recommended: string;
  maximum: string;

  // Settings
  enabled: string;
  enableProtection: string;
  notifications: string;
  showNotifications: string;
  language: string;
  selectLanguage: string;
  protectedPlatforms: string;
  howAggressive: string;

  // Alerts
  noAlerts: string;
  noAlertsDesc: string;
  acknowledge: string;

  // Warning modal
  warningTitle: string;
  sensitiveDataDetected: string;
  detectedItems: string;
  removeAll: string;
  maskData: string;
  sendAnyway: string;
  cancel: string;

  // Content script messages
  criticalIssues: string;
  sensitiveItems: string;
  itemsToReview: string;
  piiDetected: string;
  walletThreat: string;
  pageScanComplete: string;
  noSensitiveData: string;
  clipboardWarning: string;
  clipboardSafe: string;

  // Agent Shield
  agentShield: string;
  connectedAgents: string;
  noAgentsConnected: string;
  noAgentsConnectedDesc: string;
  agentConnected: string;
  agentDisconnected: string;
  trustLevel: string;
  actionsApproved: string;
  actionsRejected: string;
  memoryInjectionDetected: string;
  disconnectAgent: string;

  // MCP Gateway
  mcpGateway: string;
  registeredServers: string;
  noServersRegistered: string;
  noServersRegisteredDesc: string;
  serverRegistered: string;
  serverRemoved: string;
  trustedServer: string;
  untrustedServer: string;
  toolsAvailable: string;

  // Approval System
  approvalSystem: string;
  pendingApprovals: string;
  noPendingApprovals: string;
  noPendingApprovalsDesc: string;
  approve: string;
  reject: string;
  modify: string;
  riskLevel: string;
  riskLow: string;
  riskMedium: string;
  riskHigh: string;
  riskCritical: string;
  actionType: string;
  source: string;
  requestedBy: string;
  expiresIn: string;
  expired: string;
  autoApproved: string;
  autoRejected: string;
  manuallyApproved: string;
  manuallyRejected: string;

  // Approval Rules
  approvalRules: string;
  createRule: string;
  editRule: string;
  deleteRule: string;
  ruleName: string;
  ruleDescription: string;
  rulePriority: string;
  ruleConditions: string;
  ruleAction: string;
  ruleEnabled: string;
  noRules: string;
  noRulesDesc: string;
  autoApprove: string;
  autoReject: string;
  requireApproval: string;

  // Action History
  actionHistory: string;
  noHistory: string;
  noHistoryDesc: string;
  clearHistory: string;
  viewDetails: string;

  // New UI Components (Phase 2)
  loading: string;
  agents: string;
  mcp: string;
  agentsConnected: string;
  history: string;
  noAgentsDesc: string;
  actionsIntercepted: string;
  approved: string;
  rejected: string;
  disconnect: string;
  noPendingDesc: string;
  reviewAction: string;
  overview: string;
  thspGates: string;
  parameters: string;
  description: string;
  estimatedValue: string;
  thspOverall: string;
  passed: string;
  failed: string;
  summary: string;
  score: string;
  decisionReason: string;
  enterReason: string;
  reasonRequired: string;
  servers: string;
  tools: string;
  noMCPServers: string;
  noMCPServersDesc: string;
  clickToToggleTrust: string;
  trusted: string;
  untrusted: string;
  toolCalls: string;
  unregister: string;
  noTools: string;
  noToolsDesc: string;
  noToolHistory: string;
  noToolHistoryDesc: string;

  // Error handling & confirmations
  confirm: string;
  confirmDisconnect: string;
  confirmUnregister: string;
  errorOccurred: string;
  unexpectedError: string;
  tryAgain: string;
  errorDetails: string;
  retry: string;
  dismiss: string;

  // Rules & History (Phase 4)
  newRule: string;
  export: string;
  import: string;
  createFirstRule: string;
  deleteRuleConfirm: string;
  name: string;
  priority: string;
  conditions: string;
  action: string;
  reason: string;
  save: string;
  disable: string;
  enable: string;
  edit: string;
  delete: string;
  allSources: string;
  allDecisions: string;
  clear: string;
  clearHistoryConfirm: string;
  agent: string;
  server: string;
  processedAt: string;
  method: string;
  ruleId: string;
}

const translations: Record<Language, Translations> = {
  en: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protected',
    disabled: 'Disabled',

    // Navigation
    dashboard: 'Dashboard',
    alerts: 'Alerts',
    settings: 'Settings',
    agentMonitor: 'Agents',
    approvals: 'Approvals',
    rules: 'Rules',

    // Dashboard
    threatsBlocked: 'Threats Blocked',
    secretsCaught: 'Secrets Caught',
    sessionsProtected: 'Sessions Protected',
    protection: 'protection',
    quickActions: 'Quick Actions',
    scanPage: 'Scan Page',
    checkClipboard: 'Check Clipboard',

    // Protection levels
    protectionLevel: 'Protection Level',
    basic: 'Basic',
    recommended: 'Recommended',
    maximum: 'Maximum',

    // Settings
    enabled: 'Enabled',
    enableProtection: 'Enable protection',
    notifications: 'Notifications',
    showNotifications: 'Show desktop notifications',
    language: 'Language',
    selectLanguage: 'Select language',
    protectedPlatforms: 'Protected Platforms',
    howAggressive: 'How aggressive should protection be?',

    // Alerts
    noAlerts: 'No alerts',
    noAlertsDesc: 'You\'re all clear! No security alerts.',
    acknowledge: 'Acknowledge',

    // Warning modal
    warningTitle: 'Security Warning',
    sensitiveDataDetected: 'Sensitive data detected in your message',
    detectedItems: 'Detected items',
    removeAll: 'Remove All',
    maskData: 'Mask Data',
    sendAnyway: 'Send Anyway',
    cancel: 'Cancel',

    // Content script messages
    criticalIssues: 'critical issue(s)',
    sensitiveItems: 'sensitive item(s) detected',
    itemsToReview: 'item(s) to review',
    piiDetected: 'PII item(s) detected',
    walletThreat: 'Wallet threat detected',
    pageScanComplete: 'Page scan complete',
    noSensitiveData: 'No sensitive data found',
    clipboardWarning: 'sensitive item(s) found in clipboard!',
    clipboardSafe: 'Clipboard is safe',

    // Agent Shield
    agentShield: 'Agent Shield',
    connectedAgents: 'Connected Agents',
    noAgentsConnected: 'No Agents Connected',
    noAgentsConnectedDesc: 'Connect an AI agent to monitor its actions.',
    agentConnected: 'Agent Connected',
    agentDisconnected: 'Agent Disconnected',
    trustLevel: 'Trust Level',
    actionsApproved: 'Actions Approved',
    actionsRejected: 'Actions Rejected',
    memoryInjectionDetected: 'Memory Injection Detected',
    disconnectAgent: 'Disconnect Agent',

    // MCP Gateway
    mcpGateway: 'MCP Gateway',
    registeredServers: 'Registered Servers',
    noServersRegistered: 'No Servers Registered',
    noServersRegisteredDesc: 'Register an MCP server to monitor tool calls.',
    serverRegistered: 'Server Registered',
    serverRemoved: 'Server Removed',
    trustedServer: 'Trusted Server',
    untrustedServer: 'Untrusted Server',
    toolsAvailable: 'Tools Available',

    // Approval System
    approvalSystem: 'Approval System',
    pendingApprovals: 'Pending Approvals',
    noPendingApprovals: 'No Pending Approvals',
    noPendingApprovalsDesc: 'All actions have been processed.',
    approve: 'Approve',
    reject: 'Reject',
    modify: 'Modify',
    riskLevel: 'Risk Level',
    riskLow: 'Low',
    riskMedium: 'Medium',
    riskHigh: 'High',
    riskCritical: 'Critical',
    actionType: 'Action Type',
    source: 'Source',
    requestedBy: 'Requested by',
    expiresIn: 'Expires in',
    expired: 'Expired',
    autoApproved: 'Auto-approved',
    autoRejected: 'Auto-rejected',
    manuallyApproved: 'Manually approved',
    manuallyRejected: 'Manually rejected',

    // Approval Rules
    approvalRules: 'Approval Rules',
    createRule: 'Create Rule',
    editRule: 'Edit Rule',
    deleteRule: 'Delete Rule',
    ruleName: 'Rule Name',
    ruleDescription: 'Description',
    rulePriority: 'Priority',
    ruleConditions: 'Conditions',
    ruleAction: 'Action',
    ruleEnabled: 'Enabled',
    noRules: 'No Rules',
    noRulesDesc: 'Create rules to automate approval decisions.',
    autoApprove: 'Auto-approve',
    autoReject: 'Auto-reject',
    requireApproval: 'Require Approval',

    // Action History
    actionHistory: 'Action History',
    noHistory: 'No History',
    noHistoryDesc: 'No actions have been processed yet.',
    clearHistory: 'Clear History',
    viewDetails: 'View Details',

    // New UI Components (Phase 2)
    loading: 'Loading...',
    agents: 'Agents',
    mcp: 'MCP',
    agentsConnected: 'Agents Connected',
    history: 'History',
    noAgentsDesc: 'Connect an AI agent to start monitoring.',
    actionsIntercepted: 'Intercepted',
    approved: 'Approved',
    rejected: 'Rejected',
    disconnect: 'Disconnect',
    noPendingDesc: 'All actions have been processed.',
    reviewAction: 'Review Action',
    overview: 'Overview',
    thspGates: 'THSP Gates',
    parameters: 'Parameters',
    description: 'Description',
    estimatedValue: 'Estimated Value',
    thspOverall: 'THSP Overall',
    passed: 'Passed',
    failed: 'Failed',
    summary: 'Summary',
    score: 'Score',
    decisionReason: 'Decision Reason',
    enterReason: 'Enter your reason for this decision...',
    reasonRequired: 'Please provide a reason for your decision.',
    servers: 'Servers',
    tools: 'Tools',
    noMCPServers: 'No MCP Servers',
    noMCPServersDesc: 'Register an MCP server to start monitoring.',
    clickToToggleTrust: 'Click to toggle trust status',
    trusted: 'Trusted',
    untrusted: 'Untrusted',
    toolCalls: 'Tool Calls',
    unregister: 'Unregister',
    noTools: 'No Tools',
    noToolsDesc: 'Register MCP servers to see available tools.',
    noToolHistory: 'No Tool History',
    noToolHistoryDesc: 'Tool calls will appear here.',

    // Error handling & confirmations
    confirm: 'Confirm',
    confirmDisconnect: 'Are you sure you want to disconnect',
    confirmUnregister: 'Are you sure you want to unregister',
    errorOccurred: 'Something went wrong',
    unexpectedError: 'An unexpected error occurred',
    tryAgain: 'Try Again',
    errorDetails: 'Error Details',
    retry: 'Retry',
    dismiss: 'Dismiss',

    // Rules & History (Phase 4)
    newRule: 'New Rule',
    export: 'Export',
    import: 'Import',
    createFirstRule: 'Create your first rule',
    deleteRuleConfirm: 'Are you sure you want to delete this rule?',
    name: 'Name',
    priority: 'Priority',
    conditions: 'Conditions',
    action: 'Action',
    reason: 'Reason',
    save: 'Save',
    disable: 'Disable',
    enable: 'Enable',
    edit: 'Edit',
    delete: 'Delete',
    allSources: 'All Sources',
    allDecisions: 'All Decisions',
    clear: 'Clear',
    clearHistoryConfirm: 'Are you sure you want to clear all history? This cannot be undone.',
    agent: 'Agent',
    server: 'Server',
    processedAt: 'Processed At',
    method: 'Method',
    ruleId: 'Rule ID',
  },

  es: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protegido',
    disabled: 'Desactivado',

    // Navigation
    dashboard: 'Panel',
    alerts: 'Alertas',
    settings: 'Ajustes',
    agentMonitor: 'Agentes',
    approvals: 'Aprobaciones',
    rules: 'Reglas',

    // Dashboard
    threatsBlocked: 'Amenazas Bloqueadas',
    secretsCaught: 'Secretos Detectados',
    sessionsProtected: 'Sesiones Protegidas',
    protection: 'protección',
    quickActions: 'Acciones Rápidas',
    scanPage: 'Escanear Página',
    checkClipboard: 'Verificar Portapapeles',

    // Protection levels
    protectionLevel: 'Nivel de Protección',
    basic: 'Básico',
    recommended: 'Recomendado',
    maximum: 'Máximo',

    // Settings
    enabled: 'Activado',
    enableProtection: 'Activar protección',
    notifications: 'Notificaciones',
    showNotifications: 'Mostrar notificaciones de escritorio',
    language: 'Idioma',
    selectLanguage: 'Seleccionar idioma',
    protectedPlatforms: 'Plataformas Protegidas',
    howAggressive: '¿Qué tan agresiva debe ser la protección?',

    // Alerts
    noAlerts: 'Sin alertas',
    noAlertsDesc: '¡Todo limpio! No hay alertas de seguridad.',
    acknowledge: 'Reconocer',

    // Warning modal
    warningTitle: 'Advertencia de Seguridad',
    sensitiveDataDetected: 'Se detectaron datos sensibles en tu mensaje',
    detectedItems: 'Elementos detectados',
    removeAll: 'Eliminar Todo',
    maskData: 'Enmascarar Datos',
    sendAnyway: 'Enviar de Todos Modos',
    cancel: 'Cancelar',

    // Content script messages
    criticalIssues: 'problema(s) crítico(s)',
    sensitiveItems: 'elemento(s) sensible(s) detectado(s)',
    itemsToReview: 'elemento(s) para revisar',
    piiDetected: 'elemento(s) PII detectado(s)',
    walletThreat: 'Amenaza de billetera detectada',
    pageScanComplete: 'Escaneo de página completo',
    noSensitiveData: 'No se encontraron datos sensibles',
    clipboardWarning: '¡elemento(s) sensible(s) encontrado(s) en el portapapeles!',
    clipboardSafe: 'El portapapeles está seguro',

    // Agent Shield
    agentShield: 'Agent Shield',
    connectedAgents: 'Agentes Conectados',
    noAgentsConnected: 'Sin Agentes Conectados',
    noAgentsConnectedDesc: 'Conecta un agente de IA para monitorear sus acciones.',
    agentConnected: 'Agente Conectado',
    agentDisconnected: 'Agente Desconectado',
    trustLevel: 'Nivel de Confianza',
    actionsApproved: 'Acciones Aprobadas',
    actionsRejected: 'Acciones Rechazadas',
    memoryInjectionDetected: 'Inyección de Memoria Detectada',
    disconnectAgent: 'Desconectar Agente',

    // MCP Gateway
    mcpGateway: 'MCP Gateway',
    registeredServers: 'Servidores Registrados',
    noServersRegistered: 'Sin Servidores Registrados',
    noServersRegisteredDesc: 'Registra un servidor MCP para monitorear llamadas de herramientas.',
    serverRegistered: 'Servidor Registrado',
    serverRemoved: 'Servidor Eliminado',
    trustedServer: 'Servidor Confiable',
    untrustedServer: 'Servidor No Confiable',
    toolsAvailable: 'Herramientas Disponibles',

    // Approval System
    approvalSystem: 'Sistema de Aprobación',
    pendingApprovals: 'Aprobaciones Pendientes',
    noPendingApprovals: 'Sin Aprobaciones Pendientes',
    noPendingApprovalsDesc: 'Todas las acciones han sido procesadas.',
    approve: 'Aprobar',
    reject: 'Rechazar',
    modify: 'Modificar',
    riskLevel: 'Nivel de Riesgo',
    riskLow: 'Bajo',
    riskMedium: 'Medio',
    riskHigh: 'Alto',
    riskCritical: 'Crítico',
    actionType: 'Tipo de Acción',
    source: 'Origen',
    requestedBy: 'Solicitado por',
    expiresIn: 'Expira en',
    expired: 'Expirado',
    autoApproved: 'Auto-aprobado',
    autoRejected: 'Auto-rechazado',
    manuallyApproved: 'Aprobado manualmente',
    manuallyRejected: 'Rechazado manualmente',

    // Approval Rules
    approvalRules: 'Reglas de Aprobación',
    createRule: 'Crear Regla',
    editRule: 'Editar Regla',
    deleteRule: 'Eliminar Regla',
    ruleName: 'Nombre de Regla',
    ruleDescription: 'Descripción',
    rulePriority: 'Prioridad',
    ruleConditions: 'Condiciones',
    ruleAction: 'Acción',
    ruleEnabled: 'Activado',
    noRules: 'Sin Reglas',
    noRulesDesc: 'Crea reglas para automatizar decisiones de aprobación.',
    autoApprove: 'Auto-aprobar',
    autoReject: 'Auto-rechazar',
    requireApproval: 'Requiere Aprobación',

    // Action History
    actionHistory: 'Historial de Acciones',
    noHistory: 'Sin Historial',
    noHistoryDesc: 'Aún no se han procesado acciones.',
    clearHistory: 'Limpiar Historial',
    viewDetails: 'Ver Detalles',

    // New UI Components (Phase 2)
    loading: 'Cargando...',
    agents: 'Agentes',
    mcp: 'MCP',
    agentsConnected: 'Agentes Conectados',
    history: 'Historial',
    noAgentsDesc: 'Conecta un agente de IA para comenzar a monitorear.',
    actionsIntercepted: 'Interceptadas',
    approved: 'Aprobadas',
    rejected: 'Rechazadas',
    disconnect: 'Desconectar',
    noPendingDesc: 'Todas las acciones han sido procesadas.',
    reviewAction: 'Revisar Acción',
    overview: 'Resumen',
    thspGates: 'Puertas THSP',
    parameters: 'Parámetros',
    description: 'Descripción',
    estimatedValue: 'Valor Estimado',
    thspOverall: 'THSP General',
    passed: 'Aprobado',
    failed: 'Fallido',
    summary: 'Resumen',
    score: 'Puntuación',
    decisionReason: 'Razón de la Decisión',
    enterReason: 'Ingresa tu razón para esta decisión...',
    reasonRequired: 'Por favor proporciona una razón para tu decisión.',
    servers: 'Servidores',
    tools: 'Herramientas',
    noMCPServers: 'Sin Servidores MCP',
    noMCPServersDesc: 'Registra un servidor MCP para comenzar a monitorear.',
    clickToToggleTrust: 'Clic para cambiar estado de confianza',
    trusted: 'Confiable',
    untrusted: 'No Confiable',
    toolCalls: 'Llamadas de Herramientas',
    unregister: 'Desregistrar',
    noTools: 'Sin Herramientas',
    noToolsDesc: 'Registra servidores MCP para ver herramientas disponibles.',
    noToolHistory: 'Sin Historial de Herramientas',
    noToolHistoryDesc: 'Las llamadas de herramientas aparecerán aquí.',

    // Error handling & confirmations
    confirm: 'Confirmar',
    confirmDisconnect: '¿Estás seguro de que deseas desconectar',
    confirmUnregister: '¿Estás seguro de que deseas desregistrar',
    errorOccurred: 'Algo salió mal',
    unexpectedError: 'Ocurrió un error inesperado',
    tryAgain: 'Reintentar',
    errorDetails: 'Detalles del Error',
    retry: 'Reintentar',
    dismiss: 'Descartar',

    // Rules & History (Phase 4)
    newRule: 'Nueva Regla',
    export: 'Exportar',
    import: 'Importar',
    createFirstRule: 'Crear tu primera regla',
    deleteRuleConfirm: '¿Estás seguro de que deseas eliminar esta regla?',
    name: 'Nombre',
    priority: 'Prioridad',
    conditions: 'Condiciones',
    action: 'Acción',
    reason: 'Razón',
    save: 'Guardar',
    disable: 'Desactivar',
    enable: 'Activar',
    edit: 'Editar',
    delete: 'Eliminar',
    allSources: 'Todas las Fuentes',
    allDecisions: 'Todas las Decisiones',
    clear: 'Limpiar',
    clearHistoryConfirm: '¿Estás seguro de que deseas borrar todo el historial? Esto no se puede deshacer.',
    agent: 'Agente',
    server: 'Servidor',
    processedAt: 'Procesado En',
    method: 'Método',
    ruleId: 'ID de Regla',
  },

  pt: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protegido',
    disabled: 'Desativado',

    // Navigation
    dashboard: 'Painel',
    alerts: 'Alertas',
    settings: 'Configurações',
    agentMonitor: 'Agentes',
    approvals: 'Aprovações',
    rules: 'Regras',

    // Dashboard
    threatsBlocked: 'Ameaças Bloqueadas',
    secretsCaught: 'Segredos Detectados',
    sessionsProtected: 'Sessões Protegidas',
    protection: 'proteção',
    quickActions: 'Ações Rápidas',
    scanPage: 'Escanear Página',
    checkClipboard: 'Verificar Área de Transferência',

    // Protection levels
    protectionLevel: 'Nível de Proteção',
    basic: 'Básico',
    recommended: 'Recomendado',
    maximum: 'Máximo',

    // Settings
    enabled: 'Ativado',
    enableProtection: 'Ativar proteção',
    notifications: 'Notificações',
    showNotifications: 'Mostrar notificações na área de trabalho',
    language: 'Idioma',
    selectLanguage: 'Selecionar idioma',
    protectedPlatforms: 'Plataformas Protegidas',
    howAggressive: 'Quão agressiva deve ser a proteção?',

    // Alerts
    noAlerts: 'Sem alertas',
    noAlertsDesc: 'Tudo limpo! Nenhum alerta de segurança.',
    acknowledge: 'Reconhecer',

    // Warning modal
    warningTitle: 'Aviso de Segurança',
    sensitiveDataDetected: 'Dados sensíveis detectados na sua mensagem',
    detectedItems: 'Itens detectados',
    removeAll: 'Remover Tudo',
    maskData: 'Mascarar Dados',
    sendAnyway: 'Enviar Mesmo Assim',
    cancel: 'Cancelar',

    // Content script messages
    criticalIssues: 'problema(s) crítico(s)',
    sensitiveItems: 'item(ns) sensível(is) detectado(s)',
    itemsToReview: 'item(ns) para revisar',
    piiDetected: 'item(ns) PII detectado(s)',
    walletThreat: 'Ameaça de carteira detectada',
    pageScanComplete: 'Varredura da página completa',
    noSensitiveData: 'Nenhum dado sensível encontrado',
    clipboardWarning: 'item(ns) sensível(is) encontrado(s) na área de transferência!',
    clipboardSafe: 'Área de transferência segura',

    // Agent Shield
    agentShield: 'Agent Shield',
    connectedAgents: 'Agentes Conectados',
    noAgentsConnected: 'Nenhum Agente Conectado',
    noAgentsConnectedDesc: 'Conecte um agente de IA para monitorar suas ações.',
    agentConnected: 'Agente Conectado',
    agentDisconnected: 'Agente Desconectado',
    trustLevel: 'Nível de Confiança',
    actionsApproved: 'Ações Aprovadas',
    actionsRejected: 'Ações Rejeitadas',
    memoryInjectionDetected: 'Injeção de Memória Detectada',
    disconnectAgent: 'Desconectar Agente',

    // MCP Gateway
    mcpGateway: 'MCP Gateway',
    registeredServers: 'Servidores Registrados',
    noServersRegistered: 'Nenhum Servidor Registrado',
    noServersRegisteredDesc: 'Registre um servidor MCP para monitorar chamadas de ferramentas.',
    serverRegistered: 'Servidor Registrado',
    serverRemoved: 'Servidor Removido',
    trustedServer: 'Servidor Confiável',
    untrustedServer: 'Servidor Não Confiável',
    toolsAvailable: 'Ferramentas Disponíveis',

    // Approval System
    approvalSystem: 'Sistema de Aprovação',
    pendingApprovals: 'Aprovações Pendentes',
    noPendingApprovals: 'Nenhuma Aprovação Pendente',
    noPendingApprovalsDesc: 'Todas as ações foram processadas.',
    approve: 'Aprovar',
    reject: 'Rejeitar',
    modify: 'Modificar',
    riskLevel: 'Nível de Risco',
    riskLow: 'Baixo',
    riskMedium: 'Médio',
    riskHigh: 'Alto',
    riskCritical: 'Crítico',
    actionType: 'Tipo de Ação',
    source: 'Origem',
    requestedBy: 'Solicitado por',
    expiresIn: 'Expira em',
    expired: 'Expirado',
    autoApproved: 'Auto-aprovado',
    autoRejected: 'Auto-rejeitado',
    manuallyApproved: 'Aprovado manualmente',
    manuallyRejected: 'Rejeitado manualmente',

    // Approval Rules
    approvalRules: 'Regras de Aprovação',
    createRule: 'Criar Regra',
    editRule: 'Editar Regra',
    deleteRule: 'Excluir Regra',
    ruleName: 'Nome da Regra',
    ruleDescription: 'Descrição',
    rulePriority: 'Prioridade',
    ruleConditions: 'Condições',
    ruleAction: 'Ação',
    ruleEnabled: 'Ativado',
    noRules: 'Sem Regras',
    noRulesDesc: 'Crie regras para automatizar decisões de aprovação.',
    autoApprove: 'Auto-aprovar',
    autoReject: 'Auto-rejeitar',
    requireApproval: 'Requer Aprovação',

    // Action History
    actionHistory: 'Histórico de Ações',
    noHistory: 'Sem Histórico',
    noHistoryDesc: 'Nenhuma ação foi processada ainda.',
    clearHistory: 'Limpar Histórico',
    viewDetails: 'Ver Detalhes',

    // New UI Components (Phase 2)
    loading: 'Carregando...',
    agents: 'Agentes',
    mcp: 'MCP',
    agentsConnected: 'Agentes Conectados',
    history: 'Histórico',
    noAgentsDesc: 'Conecte um agente de IA para começar a monitorar.',
    actionsIntercepted: 'Interceptadas',
    approved: 'Aprovadas',
    rejected: 'Rejeitadas',
    disconnect: 'Desconectar',
    noPendingDesc: 'Todas as ações foram processadas.',
    reviewAction: 'Revisar Ação',
    overview: 'Visão Geral',
    thspGates: 'Portões THSP',
    parameters: 'Parâmetros',
    description: 'Descrição',
    estimatedValue: 'Valor Estimado',
    thspOverall: 'THSP Geral',
    passed: 'Aprovado',
    failed: 'Falhou',
    summary: 'Resumo',
    score: 'Pontuação',
    decisionReason: 'Razão da Decisão',
    enterReason: 'Digite sua razão para esta decisão...',
    reasonRequired: 'Por favor forneça uma razão para sua decisão.',
    servers: 'Servidores',
    tools: 'Ferramentas',
    noMCPServers: 'Sem Servidores MCP',
    noMCPServersDesc: 'Registre um servidor MCP para começar a monitorar.',
    clickToToggleTrust: 'Clique para alternar status de confiança',
    trusted: 'Confiável',
    untrusted: 'Não Confiável',
    toolCalls: 'Chamadas de Ferramentas',
    unregister: 'Remover Registro',
    noTools: 'Sem Ferramentas',
    noToolsDesc: 'Registre servidores MCP para ver ferramentas disponíveis.',
    noToolHistory: 'Sem Histórico de Ferramentas',
    noToolHistoryDesc: 'Chamadas de ferramentas aparecerão aqui.',

    // Error handling & confirmations
    confirm: 'Confirmar',
    confirmDisconnect: 'Tem certeza que deseja desconectar',
    confirmUnregister: 'Tem certeza que deseja remover o registro de',
    errorOccurred: 'Algo deu errado',
    unexpectedError: 'Ocorreu um erro inesperado',
    tryAgain: 'Tentar Novamente',
    errorDetails: 'Detalhes do Erro',
    retry: 'Tentar novamente',
    dismiss: 'Dispensar',

    // Rules & History (Phase 4)
    newRule: 'Nova Regra',
    export: 'Exportar',
    import: 'Importar',
    createFirstRule: 'Criar sua primeira regra',
    deleteRuleConfirm: 'Tem certeza que deseja excluir esta regra?',
    name: 'Nome',
    priority: 'Prioridade',
    conditions: 'Condições',
    action: 'Ação',
    reason: 'Motivo',
    save: 'Salvar',
    disable: 'Desativar',
    enable: 'Ativar',
    edit: 'Editar',
    delete: 'Excluir',
    allSources: 'Todas as Fontes',
    allDecisions: 'Todas as Decisões',
    clear: 'Limpar',
    clearHistoryConfirm: 'Tem certeza que deseja limpar todo o histórico? Esta ação não pode ser desfeita.',
    agent: 'Agente',
    server: 'Servidor',
    processedAt: 'Processado Em',
    method: 'Método',
    ruleId: 'ID da Regra',
  },
};

// Current language (will be loaded from storage)
let currentLanguage: Language = 'en';

/**
 * Set the current language
 */
export function setLanguage(lang: Language): void {
  currentLanguage = lang;
}

/**
 * Get the current language
 */
export function getLanguage(): Language {
  return currentLanguage;
}

/**
 * Get translation for a key
 */
export function t(key: keyof Translations): string {
  return translations[currentLanguage][key] || translations.en[key] || key;
}

/**
 * Get all translations for current language
 */
export function getTranslations(): Translations {
  return translations[currentLanguage];
}

/**
 * Get available languages
 */
export function getAvailableLanguages(): { code: Language; name: string }[] {
  return [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'pt', name: 'Português' },
  ];
}

/**
 * Detect browser language and return closest match
 */
export function detectBrowserLanguage(): Language {
  const browserLang = navigator.language.toLowerCase().split('-')[0];
  if (browserLang === 'es') return 'es';
  if (browserLang === 'pt') return 'pt';
  return 'en';
}
