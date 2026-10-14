#!/usr/bin/env python3
"""Apply a PT-BR localization patch to the checked-out Mamu submodule for CI builds.

The upstream submodule is not edited or committed. This script runs only in the
CI workspace after checkout, preserving the original upstream repository.
"""
from pathlib import Path
import re
import html

ROOT = Path("vendor/Mamu/app")
STRINGS = ROOT / "src/main/res/values/strings.xml"

TRANSLATIONS = {
    "app_name": "Mamu - Português",
    "close_fullscreen_content_desc": "Fechar",
    "settings_title": "Configurações",
    "settings_quick_actions": "Ações rápidas",
    "settings_select_process": "Selecionar processo",
    "settings_no_process_selected": "Nenhum processo selecionado",
    "settings_terminate_proc": "Encerrar processo",
    "settings_exit": "Fechar janela flutuante",
    "settings_process_settings": "Configurações do processo",
    "settings_memory_range": "Selecionar regiões de memória",
    "settings_memory_range_summary": "Toque para escolher as regiões de memória da busca",
    "settings_hide_mamu": "Ocultar Mamu do processo",
    "settings_hide_mode_1": "Modo de ocultação 1",
    "settings_hide_mode_2": "Modo de ocultação 2",
    "settings_hide_mode_3": "Modo de ocultação 3",
    "settings_hide_mode_4": "Modo de ocultação 4",
    "settings_skip_memory": "Ignorar regiões de memória",
    "settings_skip_memory_none": "Não",
    "settings_skip_memory_empty": "Vazias",
    "settings_skip_memory_empty_zygote": "Vazias ou Zygote",
    "settings_auto_pause": "Pausar processo ao abrir a janela flutuante",
    "settings_freeze_interval": "Intervalo de congelamento",
    "settings_search_settings": "Configurações de busca",
    "settings_chunk_size": "Tamanho do bloco de busca",
    "settings_chunk_size_summary": "Quantidade de memória lida em cada etapa da busca",
    "settings_rude_search": "Busca simplificada",
    "settings_rude_search_summary": "Ignora páginas possivelmente vazias; é mais rápido, mas pode deixar dados passar",
    "settings_failed_page_threshold": "Limite de páginas com falha consecutivas",
    "settings_failed_page_threshold_summary": "Ignora um bloco de 256 KB ao atingir o limite",
    "settings_general_settings": "Configurações gerais",
    "settings_filter_system_process": "Filtrar processos do sistema",
    "settings_filter_linux_process": "Filtrar processos Linux",
    "settings_list_update_interval": "Intervalo de atualização da lista salva",
    "settings_memory_rw_mode": "Modo de leitura e escrita da memória",
    "settings_memory_rw_mode_none": "Nenhum",
    "settings_memory_rw_mode_writethrough": "Gravação direta (lenta)",
    "settings_memory_rw_mode_nocache": "Sem cache (lento)",
    "settings_memory_rw_mode_normal": "Normal (lento)",
    "settings_memory_rw_mode_pgfault": "Acesso por falha de página (mais rápido)",
    "settings_opacity": "Opacidade",
    "settings_memory_buffer_size": "Tamanho do buffer de memória",
    "settings_memory_buffer_size_summary": "Buffer dos resultados da busca; reinicie o app após alterar",
    "settings_dialog_transparency": "Transparência das janelas",
    "settings_dialog_transparency_summary": "Desative para deixar as janelas totalmente opacas",
    "settings_compatibility_mode": "Modo de compatibilidade",
    "settings_compatibility_mode_summary": "Armazena resultados em formato aproximado para alternar entre busca exata e aproximada",
    "settings_top_most_layer": "Manter janela sempre no topo",
    "settings_top_most_layer_summary": "Exibe a janela flutuante sobre outros apps; pode ficar instável",
    "settings_ui_settings": "Configurações da interface",
    "settings_keyboard": "Teclado",
    "settings_keyboard_builtin": "Integrado",
    "settings_keyboard_system": "Teclado do sistema",
    "settings_language": "Idioma",
    "settings_language_zh_cn": "Português (Brasil)",
    "settings_language_en": "English",
    "settings_memory_preview_infinite_scroll": "Rolagem contínua na prévia da memória",
    "settings_memory_preview_infinite_scroll_summary": "Desativado: mostra somente uma página de memória",
    "success_infinite_scroll_enabled": "Rolagem contínua ativada; aplique ao navegar para outro endereço",
    "success_infinite_scroll_disabled": "Rolagem contínua desativada; aplique ao navegar para outro endereço",
    "dialog_select_operator": "Selecionar operador",
    "dialog_select_memory_range": "Selecionar regiões de memória",
    "dialog_skip_memory_title": "Ignorar regiões de memória",
    "memory_empty_region": "Região vazia",
    "memory_range_unselected": "Nenhuma região de memória selecionada",
    "memory_range_count": "%d regiões selecionadas",
    "success_process_terminated": "Processo encerrado",
    "success_process_selected": "Processo selecionado: %s",
    "success_memory_range_saved": "Regiões de memória salvas",
    "success_skip_memory_saved": "Configuração de regiões ignoradas salva",
    "success_memory_rw_mode_saved": "Modo de leitura/escrita salvo",
    "success_memory_buffer_size_saved": "Tamanho do buffer salvo; reinicie o app para aplicar",
    "success_keyboard_saved": "Configuração do teclado salva",
    "success_language_saved": "Idioma salvo",
    "success_chunk_size_saved": "Tamanho do bloco de busca salvo",
    "success_compatibility_mode_enabled": "Modo de compatibilidade ativado",
    "success_compatibility_mode_disabled": "Modo de compatibilidade desativado",
    "success_topmost_changed": "Janela sempre no topo %s; reinicie a janela flutuante para aplicar",
    "topmost_enabled": "ativada",
    "topmost_disabled": "desativada",
    "success_search_complete": "%1$d resultados encontrados em %2$s",
    "search_cancelled": "Busca cancelada",
    "error_topmost_fallback": "Modo sempre no topo indisponível; usando o modo normal",
    "error_process_died": "O processo foi encerrado (PID: %d)",
    "error_terminate_failed": "Não foi possível encerrar o processo",
    "error_no_bound_process": "Nenhum processo vinculado",
    "error_bind_process_failed": "Não foi possível vincular o processo",
    "error_bind_process_failed_with_reason": "Falha ao vincular o processo: %s",
    "error_empty_search_value": "Digite um valor para buscar",
    "feature_convert_base_todo": "Conversão de base ainda não implementada",
    "feature_select_memory_range_todo": "Seleção de regiões de memória ainda não implementada",
    "feature_history_todo": "Histórico ainda não implementado",
    "placeholder_process_name": "Nome do processo",
    "button_cancel": "Cancelar",
    "button_confirm": "Confirmar",
    "content_desc_menu": "Item do menu",
    "content_desc_close": "Fechar",
    "content_desc_delete": "Excluir",
    "content_desc_refresh": "Atualizar",
    "tab_settings": "Configurações",
    "tab_search": "Buscar",
    "tab_saved_addresses": "Endereços salvos",
    "tab_memory_preview": "Prévia da memória",
    "tab_breakpoints": "Pontos de interrupção",
    "pointer_scan_dialog_title": "Busca de ponteiros",
    "pointer_scan_dialog_subtitle": "Informe o endereço de destino para encontrar cadeias de ponteiros",
    "label_target_address": "Endereço de destino:",
    "hint_target_address": "Digite um endereço hexadecimal",
    "error_invalid_address": "Formato de endereço inválido",
    "error_process_not_bound": "Vincule um processo primeiro",
    "error_no_memory_regions": "Não foi possível obter as regiões de memória",
    "success_pointer_scan_started": "Busca de ponteiros iniciada",
    "success_pointer_scan_complete": "%d ponteiros encontrados",
    "warning_pointer_scan_cancelled": "Busca de ponteiros cancelada",
    "error_pointer_scan_failed": "Falha na busca: %s",
    "label_value_encrypted": "Este valor está criptografado?",
    "label_deep_search": "Busca profunda (lenta)",
    "label_value_allow_pagefault": "Acesso profundo (falha de página)",
    "label_value_freeze": "Congelar valor",
    "label_search_all_memory": "Em toda a memória",
    "button_new_search": "Nova busca",
    "button_search": "Buscar",
    "button_refine": "Refinar",
    "label_type": "Tipo:",
    "content_desc_convert_hex": "Converter base numérica",
    "label_value": "Valor:",
    "search_dialog_title": "Digite o valor para buscar",
    "search_dialog_subtitle": "Digite um valor entre -1,8e+308 e 1,8e+308",
    "dialog_remove_title": "Opções de remoção",
    "option_remove_all": "Remover tudo",
    "option_restore_and_remove": "Restaurar e remover",
    "option_remove_selected": "Remover selecionados",
    "label_remove": "Remover",
    "dialog_filter_title": "Configurar filtros",
    "label_max_display_count": "Máximo por página",
    "label_address_range_filter": "Filtro por intervalo de endereço",
    "label_address_start": "Início",
    "label_address_end": "Fim",
    "label_value_range_filter": "Filtro por intervalo de valor",
    "label_value_min": "Valor mínimo",
    "label_value_max": "Valor máximo",
    "label_data_type_filter": "Filtro por tipo de dado",
    "button_select_data_types": "Selecionar tipos de dados",
    "label_permission_filter": "Filtro por permissões",
    "button_select_permissions": "Selecionar permissões",
    "button_reset": "Redefinir",
    "button_apply": "Aplicar",
    "fuzzy_search_dialog_title": "Busca aproximada",
    "fuzzy_search_initial_title": "Busca inicial",
    "fuzzy_search_refine_title": "Refinar busca",
    "fuzzy_search_initial_subtitle": "Registra valores do tipo escolhido para permitir refinamentos posteriores",
    "fuzzy_search_refine_subtitle": "Filtra os resultados anteriores de acordo com a condição",
    "fuzzy_search_select_condition": "Selecione a condição de busca",
    "fuzzy_search_select_type": "Selecione o tipo de dado",
    "fuzzy_search_param1": "Parâmetro 1",
    "fuzzy_search_param2": "Parâmetro 2",
    "fuzzy_search_param1_hint": "Digite um valor",
    "fuzzy_search_param2_hint": "Digite um valor",
    "fuzzy_search_range_hint": "Intervalo: %1$s ~ %2$s",
    "fuzzy_search_percent_hint": "Porcentagem: 0 a 100",
    "fuzzy_search_button_start": "Iniciar busca",
    "fuzzy_search_button_refine": "Refinar",
    "fuzzy_search_no_results": "Faça uma busca inicial primeiro",
    "fuzzy_search_current_results": "Resultados atuais: %d",
    "hint_value_min": "Valor mínimo",
    "hint_value_max": "Valor máximo",
    "modify_dialog_title": "Alterar valor",
    "modify_dialog_subtitle": "Digite o novo valor",
    "button_goto": "Ir para",
    "button_no": "Não",
    "button_yes": "Sim",
    "button_copy": "Copiar",
    "modify_success_message": "Endereço %s alterado com sucesso",
    "modify_failed_message": "Falha ao alterar o endereço %s",
    "error_invalid_value_format": "Formato de valor inválido: %s",
    "error_modify_failed": "Falha ao modificar: %s",
    "permission_setup_initializing": "Inicializando...",
    "permission_setup_checking_root": "Verificando acesso root...",
    "permission_setup_root_check_hint": "Permita o acesso root na janela de autorização",
    "permission_setup_no_root_title": "Acesso root não concedido",
    "permission_setup_no_root_message": "Este aplicativo precisa de acesso root para funcionar corretamente. Verifique se o dispositivo tem root e autorize o acesso no gerenciador de permissões.",
    "permission_setup_root_granted_title": "Acesso root concedido",
    "permission_setup_root_confirm_message": "Permitir que o app conceda automaticamente as permissões de sistema necessárias usando root?",
    "permission_setup_permissions_list": "Inclui: consultar pacotes instalados e permissão de janela flutuante",
    "permission_setup_granting_title": "Concedendo permissões",
    "permission_setup_current_permission": "Permissão atual:",
    "permission_setup_completed_all": "Permissões concedidas",
    "permission_setup_completed_partial": "Algumas permissões foram concedidas",
    "permission_setup_granted_count": "%1$d de %2$d permissões concedidas",
    "permission_setup_launching": "Abrindo a tela principal…",
    "permission_setup_error_title": "Ocorreu um erro",
    "button_retry": "Tentar novamente",
    "button_skip": "Pular",
    "button_allow": "Permitir",
    "notification_channel_name": "Serviço da janela flutuante",
    "notification_channel_description": "Mantém a janela flutuante ativa em segundo plano",
    "notification_title": "Mamu está em execução",
    "notification_text": "Toque para voltar ao aplicativo",
    "home_title": "Mamu",
    "home_refresh": "Atualizar",
    "home_driver_status_title": "Status do driver",
    "home_driver_loaded": "Carregado",
    "home_driver_not_loaded": "Não carregado",
    "home_driver_error": "Erro",
    "home_driver_unknown": "Desconhecido",
    "home_driver_bound_process": "Processo vinculado",
    "home_driver_bound_process_value": "PID: %d",
    "home_driver_not_bound": "Nenhum processo vinculado",
    "home_driver_error_message": "Detalhes do erro",
    "home_root_status_title": "Permissão root",
    "home_root_granted": "Concedida",
    "home_root_not_granted": "Não concedida",
    "home_selinux_status_title": "Status do SELinux",
    "home_selinux_enforcing": "Modo obrigatório",
    "home_selinux_permissive": "Modo permissivo",
    "home_selinux_disabled": "Desativado",
    "home_selinux_unknown": "Desconhecido",
    "home_selinux_mode": "Modo",
    "home_system_info_title": "Informações do sistema",
    "home_device_model": "Modelo do dispositivo",
    "home_device_manufacturer": "Fabricante do dispositivo",
    "home_device_brand": "Marca do dispositivo",
    "home_android_version": "Versão do Android",
    "home_sdk_version": "Versão do SDK",
    "home_kernel_version": "Versão do kernel",
    "home_cpu_abi": "Arquitetura da CPU",
    "home_supported_abis": "Arquiteturas compatíveis",
    "home_error_title": "Erro",
    "searching": "Buscando...",
    "regions_searched": "Regiões pesquisadas:",
    "address_searched": "Endereços pesquisados:",
    "results_found": "Resultados encontrados:",
    "hide": "Ocultar",
}

# Translate common hard-coded Compose/View labels without changing logic.
PHRASES = {
    "首页": "Início", "模块": "Módulos", "工具": "Ferramentas", "日志": "Registros",
    "模糊搜索": "Busca aproximada", "初始扫描": "Busca inicial", "细化搜索": "Refinar busca",
    "开始扫描": "Iniciar busca", "当前结果": "Resultados atuais", "搜索条件": "Condição de busca",
    "选择数据类型": "Selecionar tipo de dado", "输入数值": "Digite um valor",
    "内存区域": "Regiões de memória", "搜索结果": "Resultados da busca",
    "权限设置": "Configurações de permissões", "权限不足": "Permissões insuficientes",
    "正在加载": "Carregando", "请稍候": "Aguarde", "没有结果": "Nenhum resultado",
    "搜索完成": "Busca concluída", "搜索失败": "Falha na busca", "修改成功": "Alterado com sucesso",
    "修改失败": "Falha ao alterar", "进程列表": "Lista de processos", "选择目标进程": "Selecionar processo de destino",
    "设置": "Configurações", "搜索": "Buscar", "保存的地址": "Endereços salvos",
    "内存预览": "Prévia da memória", "断点": "Pontos de interrupção",
    "选择进程": "Selecionar processo", "未选择进程": "Nenhum processo selecionado",
    "驱动状态": "Status do driver", "已加载": "Carregado", "未加载": "Não carregado",
    "绑定进程": "Vincular processo", "未绑定": "Não vinculado", "系统信息": "Informações do sistema",
    "设备型号": "Modelo do dispositivo", "设备制造商": "Fabricante do dispositivo",
    "设备品牌": "Marca do dispositivo", "Android版本": "Versão do Android",
    "内核版本": "Versão do kernel", "CPU架构": "Arquitetura da CPU",
    "刷新": "Atualizar", "错误": "Erro", "未知": "Desconhecido",
    "启动": "Iniciar", "停止": "Parar", "取消": "Cancelar", "确认": "Confirmar",
    "返回": "Voltar", "关闭": "Fechar", "删除": "Excluir", "保存": "Salvar",
    "工具箱": "Caixa de ferramentas", "教程": "Tutorial", "开始练习": "Começar",
    "重新开始教程": "Reiniciar tutorial",
    "教程已重置，返回首页后将再次显示新手教程。": "O tutorial foi reiniciado. Ele será exibido novamente ao voltar ao início.",
    "返回首页": "Voltar ao início",
    "通用": "Geral",
    "自动显示悬浮窗": "Mostrar janela flutuante automaticamente",
    "应用启动时自动显示悬浮窗": "Mostrar a janela flutuante ao iniciar o aplicativo",
    "重新进入教程": "Abrir tutorial novamente",
    "重新显示新手教程": "Exibir o tutorial inicial novamente",
    "关于 Mamu": "Sobre o Mamu",
    "查看版本信息、开源依赖和致谢": "Ver versão, dependências de código aberto e créditos",
    "外观": "Aparência",
    "深色模式": "Modo escuro",
    "跟随系统": "Seguir o sistema",
    "浅色": "Claro",
    "深色": "Escuro",
    "主题": "Tema",
    "动态配色": "Cores dinâmicas",
    "根据壁纸自动生成主题颜色": "Gerar cores do tema automaticamente com base no papel de parede",
    "动态配色在当前 Android 版本不可用": "As cores dinâmicas não estão disponíveis nesta versão do Android",
    "首页": "Início",
    "模块": "Módulos",
    "工具": "Ferramentas",
    "日志": "Registros",
    "功能开发中...": "Recurso em desenvolvimento...",
    "检查Root权限": "Verificar permissão root",
    "验证设备是否已获取Root权限": "Verificar se o dispositivo possui acesso root",
    "确认Root授权": "Confirmar autorização root",
    "允许应用使用Root权限": "Permitir que o aplicativo use acesso root",
    "授予系统权限": "Conceder permissões do sistema",
    "自动配置所需的系统权限": "Configurar automaticamente as permissões necessárias do sistema",
    "检查驱动": "Verificar driver",
    "验证内存驱动是否已安装": "Verificar se o driver de memória está instalado",
    "设置完成": "Configuração concluída",
    "准备启动应用": "Preparando para iniciar o aplicativo",
    "权限设置": "Configuração de permissões",
    "请按照步骤完成应用初始化": "Siga as etapas para concluir a configuração inicial do aplicativo",
    "自定义检查命令": "Comando de verificação personalizado",
    "收起": "Recolher",
    "展开": "Expandir",
    "Root检查命令": "Comando de verificação root",
    "正在初始化...": "Inicializando...",
    "正在检查Root权限": "Verificando acesso root",
    "请在弹出的授权窗口中允许Root访问": "Permita o acesso root na janela de autorização",
    "未获取Root权限": "Acesso root não concedido",
    "此应用需要Root权限才能正常运行。请确保您的设备已Root，并在授权管理器中允许访问。": "Este aplicativo precisa de acesso root para funcionar. Verifique se o dispositivo tem root e autorize o acesso no gerenciador de permissões.",
    "可以在上方的步骤中自定义Root检查命令后重试。": "Você pode personalizar o comando de verificação root nas etapas acima e tentar novamente.",
    "重试": "Tentar novamente",
    "Root权限已获取": "Acesso root concedido",
    "将使用Root权限自动授予应用所需的系统权限": "O acesso root será usado para conceder automaticamente as permissões necessárias",
    "包括：悬浮窗权限、外部存储访问权限等": "Inclui permissão de janela flutuante e acesso ao armazenamento externo",
    "开始授权": "Conceder permissões",
    "正在授予权限": "Concedendo permissões",
    "当前权限": "Permissão atual",
    "应用究极免杀保护": "Proteção avançada do aplicativo",
    "当前保护措施": "Proteções atuais",
    "正在检查驱动": "Verificando driver",
    "正在验证内存驱动是否已安装...": "Verificando se o driver de memória está instalado...",
    "驱动未安装": "Driver não instalado",
    "内存驱动尚未安装，需要安装驱动才能使用完整功能。": "O driver de memória ainda não está instalado. Instale-o para usar todos os recursos.",
    "安装驱动": "Instalar driver",
    "权限授予完成": "Permissões concedidas",
    "部分权限授予成功": "Algumas permissões foram concedidas",
    "已授予": "Concedidas",
    "项权限": "permissões",
    "正在启动主界面...": "Iniciando a tela principal...",
    "发生错误": "Ocorreu um erro",
    "关闭悬浮窗": "Fechar janela flutuante",
    "启动悬浮窗": "Iniciar janela flutuante",
    "状态概览": "Resumo do status",
    "已加载 (PID:": "Carregado (PID:",
    "已加载": "Carregado",
    "未加载": "Não carregado",
    "错误": "Erro",
    "未知": "Desconhecido",
    "驱动": "Driver",
    "已获取": "Concedido",
    "未获取": "Não concedido",
    "强制模式": "Modo enforcing",
    "宽容模式": "Modo permissivo",
    "已禁用": "Desativado",
    "安全警告": "Aviso de segurança",
    "设备信息": "Informações do dispositivo",
    "屏幕信息": "Informações da tela",
    "分辨率": "Resolução",
    "屏幕尺寸": "Tamanho da tela",
    "密度 (DPI)": "Densidade (DPI)",
    "密度系数": "Escala de densidade",
    "字体缩放": "Escala da fonte",
    "设备": "Dispositivo",
    "系统": "Sistema",
    "架构": "Arquitetura",
    "等待日志...": "Aguardando registros...",
    "点击 ▶ 开始捕获": "Toque em ▶ para começar a capturar",
    "捕获中": "Capturando",
    "条": "itens",
    "搜索引擎未初始化": "O mecanismo de busca não foi inicializado",
    "无效的搜索表达式": "Expressão de busca inválida",
    "内存读取失败": "Falha ao ler a memória",
    "搜索正在进行中": "Busca em andamento",
    "搜索出错": "Erro na busca",
    "启动搜索失败": "Falha ao iniciar a busca",
    "搜索失败": "Falha na busca",
    "特征码搜索不支持改善搜索，请使用新搜索": "A busca por padrão não permite refinar resultados. Inicie uma nova busca.",
    "启动改善搜索失败": "Falha ao iniciar o refinamento da busca",
    "改善搜索失败": "Falha ao refinar a busca",
    "已转到地址:": "Navegou para o endereço:",
    "选择内存范围": "Selecionar regiões de memória",
    "输入数值": "Digite um valor",
    "确定": "Confirmar",
    "输入百分比 (0-100)": "Digite a porcentagem (0 a 100)",
    "百分比必须在 0-100 之间": "A porcentagem deve estar entre 0 e 100",
    "输入的数值格式错误": "Formato de valor inválido",
    "请先选择进程": "Selecione um processo primeiro",
    "未选中任何进程": "Nenhum processo selecionado",
    "未选择内存范围": "Nenhuma região de memória selecionada",
    "找到": "Encontrados",
    "个maps项": "itens de mapa",
    "搜索结果获取失败": "Falha ao obter os resultados da busca",
    "搜索取消": "Busca cancelada",
    "搜索已取消": "Busca cancelada",
    "当前无已绑定进程": "Nenhum processo vinculado",
    "绑定进程失败": "Falha ao vincular processo",
    "请选择搜索值": "Digite um valor para buscar",
    "请输入搜索值": "Digite um valor para buscar",
    "新搜索": "Nova busca",
    "改善搜索": "Refinar busca",
    "搜索条件": "Condição de busca",
    "基础条件": "Condição básica",
    "增加指定值": "Aumentar por valor definido",
    "减少指定值": "Diminuir por valor definido",
    "增加百分比": "Aumentar porcentagem",
    "减少百分比": "Diminuir porcentagem",
    "输入百分比": "Digite a porcentagem",
    "未选择任何进程": "Nenhum processo selecionado",
    "未选择内存区域": "Nenhuma região de memória selecionada",
    "启动模糊搜索失败": "Falha ao iniciar a busca aproximada",
    "启动细化搜索失败": "Falha ao iniciar o refinamento",
    "搜索出错:": "Erro na busca:",
    "未选择操作符": "Nenhum operador selecionado",
    "选择操作符": "Selecionar operador",
    "退出悬浮窗": "Sair da janela flutuante",
    "终止进程": "Encerrar processo",
    "选择调试进程": "Selecionar processo para depuração",
    "保存的地址": "Endereços salvos",
    "内存预览": "Prévia da memória",
    "断点": "Pontos de interrupção",
    "请输入": "Digite",
    "无结果": "Nenhum resultado",
    "没有结果": "Nenhum resultado",
    "搜索完成": "Busca concluída",
    "修改成功": "Alterado com sucesso",
    "修改失败": "Falha ao alterar",
    "进程列表": "Lista de processos",
    "选择目标进程": "Selecionar processo de destino",
    "设置": "Configurações",
    "搜索": "Buscar",
    "未选择进程": "Nenhum processo selecionado",
    "驱动状态": "Status do driver",
    "未绑定": "Não vinculado",
    "绑定进程": "Vincular processo",
    "系统信息": "Informações do sistema",
    "设备型号": "Modelo do dispositivo",
    "设备制造商": "Fabricante do dispositivo",
    "设备品牌": "Marca do dispositivo",
    "Android版本": "Versão do Android",
    "内核版本": "Versão do kernel",
    "CPU架构": "Arquitetura da CPU",
    "刷新": "Atualizar",
    "启动": "Iniciar",
    "停止": "Parar",
    "取消": "Cancelar",
    "确认": "Confirmar",
    "返回": "Voltar",
    "关闭": "Fechar",
    "删除": "Excluir",
    "保存": "Salvar",
    "请稍候": "Aguarde",
    "正在加载": "Carregando",
    "页面": "Página",
    "暂无数据": "Nenhum dado disponível",
    "复制": "Copiar",
    "导入": "Importar",
    "导出": "Exportar",
    "修改": "Alterar",
    "冻结": "Congelar",
    "解冻": "Descongelar",
    "地址": "Endereço",
    "数值": "Valor",
    "类型": "Tipo",
    "名称": "Nome",
    "大小": "Tamanho",
    "权限": "Permissão",
    "进程": "Processo",
    "内存": "Memória",
    "范围": "Intervalo",
    "全部": "Todos",
    "全选": "Selecionar tudo",
    "反选": "Inverter seleção",
    "确定删除吗？": "Tem certeza de que deseja excluir?",
    "是否继续？": "Deseja continuar?",
    "请输入地址": "Digite o endereço",
    "请输入新值": "Digite o novo valor",
    "请输入名称": "Digite o nome",
    "保存成功": "Salvo com sucesso",
    "保存失败": "Falha ao salvar",
    "操作成功": "Operação concluída",
    "操作失败": "Falha na operação",
}

def patch_strings():
    if not STRINGS.exists():
        raise SystemExit(f"Arquivo de recursos do Mamu não encontrado: {STRINGS}")
    source = STRINGS.read_text(encoding="utf-8")
    changed = 0
    def replace_line(match):
        nonlocal changed
        name, attrs, value = match.group(1), match.group(2) or "", match.group(3)
        if name not in TRANSLATIONS:
            return match.group(0)
        new_value = TRANSLATIONS[name]
        if value == new_value:
            return match.group(0)
        changed += 1
        return f'<string name="{name}"{attrs}>{new_value}</string>'
    # Keep the resource file's formatting/comments intact.
    source = re.sub(r'<string name="([^"]+)"([^>]*)>(.*?)</string>', replace_line, source, flags=re.S)
    STRINGS.write_text(source, encoding="utf-8")
    print(f"PT-BR: {changed} recursos traduzidos.")

def patch_source_phrases():
    java_root = ROOT / "src/main/java"
    layout_root = ROOT / "src/main/res/layout"
    changed_files = 0
    if not java_root.exists():
        raise SystemExit(f"Código Kotlin do Mamu não encontrado: {java_root}")
    paths = list(java_root.rglob("*.kt"))
    if layout_root.exists():
        paths.extend(layout_root.rglob("*.xml"))
    for path in paths:
        original = path.read_text(encoding="utf-8")
        updated = original
        for source, target in sorted(PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
            updated = updated.replace(source, target)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
    print(f"PT-BR: textos embutidos traduzidos em {changed_files} arquivos Kotlin.")


def patch_startup_compatibility():
    """Prevent native initialization failures from silently terminating the app."""
    app_file = ROOT / "src/main/java/moe/fuqiuluo/mamu/MamuApplication.kt"
    activity_file = ROOT / "src/main/java/moe/fuqiuluo/mamu/PermissionSetupActivity.kt"
    app = app_file.read_text(encoding="utf-8")

    app = app.replace("import kotlin.system.exitProcess\n", "")
    old_companion = """    companion object {
        lateinit var instance: MamuApplication
            private set

        init {
            System.loadLibrary("mamu_core")
        }
    }"""
    new_companion = """    companion object {
        lateinit var instance: MamuApplication
            private set

        @Volatile
        var startupError: String? = null
            private set

        private var nativeLibraryLoaded = false

        init {
            try {
                System.loadLibrary("mamu_core")
                nativeLibraryLoaded = true
            } catch (error: Throwable) {
                startupError = "A biblioteca nativa do Mamu não está disponível para a arquitetura deste dispositivo."
                Log.e(TAG, "Não foi possível carregar mamu_core", error)
            }
        }
    }"""
    if old_companion in app:
        app = app.replace(old_companion, new_companion, 1)

    old_core = """        if (!initMamuCore()) {
            Log.e(TAG, "Failed to initialize Mamu Core")
            exitProcess(1)
        }"""
    new_core = """        if (!nativeLibraryLoaded) {
            Log.e(TAG, startupError ?: "Biblioteca nativa indisponível")
            return
        }

        val coreReady = try {
            initMamuCore()
        } catch (error: Throwable) {
            Log.e(TAG, "Falha ao inicializar o núcleo nativo do Mamu", error)
            startupError = "O núcleo nativo não conseguiu iniciar neste dispositivo. Verifique a compatibilidade da arquitetura e a versão do Android."
            false
        }
        if (!coreReady) {
            if (startupError == null) {
                startupError = "O núcleo nativo do Mamu não conseguiu inicializar neste dispositivo."
            }
            Log.e(TAG, startupError ?: "Falha ao inicializar Mamu Core")
            return
        }"""
    if old_core in app:
        app = app.replace(old_core, new_core, 1)

    old_search = """        if (!SearchEngine.initSearchEngine(
                bufferSize, cacheDir.absoluteFile.resolve("search_engine").also {
                    if (!it.exists()) it.mkdirs()
                }.absolutePath, chunkSizeBytes
            )
        ) {
            Log.e(TAG, "Failed to initialize Search Engine")
            exitProcess(1)
        }"""
    new_search = """        val searchReady = try {
            SearchEngine.initSearchEngine(
                bufferSize, cacheDir.absoluteFile.resolve("search_engine").also {
                    if (!it.exists()) it.mkdirs()
                }.absolutePath, chunkSizeBytes
            )
        } catch (error: Throwable) {
            Log.e(TAG, "Falha ao inicializar o mecanismo de busca", error)
            false
        }
        if (!searchReady) {
            startupError = "O mecanismo de busca não conseguiu inicializar. Tente reiniciar o aplicativo; se continuar, o dispositivo pode não ser compatível."
            Log.e(TAG, startupError ?: "Falha ao inicializar Search Engine")
            return
        }"""
    if old_search in app:
        app = app.replace(old_search, new_search, 1)

    old_pointer = """        if (!PointerScanner.init(
                cacheDir.absoluteFile.resolve("pointer_chain")
                    .also { if (!it.exists()) it.mkdirs() }.absolutePath
            )
        ) {
            Log.e(TAG, "Failed to initialize PointerScanner")
            exitProcess(1)
        }"""
    new_pointer = """        val pointerReady = try {
            PointerScanner.init(
                cacheDir.absoluteFile.resolve("pointer_chain")
                    .also { if (!it.exists()) it.mkdirs() }.absolutePath
            )
        } catch (error: Throwable) {
            Log.e(TAG, "Falha ao inicializar o scanner de ponteiros", error)
            false
        }
        if (!pointerReady) {
            startupError = "O scanner de ponteiros não conseguiu inicializar neste dispositivo."
            Log.e(TAG, startupError ?: "Falha ao inicializar PointerScanner")
            return
        }"""
    if old_pointer in app:
        app = app.replace(old_pointer, new_pointer, 1)

    app_file.write_text(app, encoding="utf-8")

    activity = activity_file.read_text(encoding="utf-8")
    old_activity = """        enableEdgeToEdge()

        setContent {
            MXTheme {"""
    new_activity = """        enableEdgeToEdge()

        val startupError = MamuApplication.startupError
        if (startupError != null) {
            setContent {
                MXTheme {
                    androidx.compose.material3.Surface {
                        androidx.compose.foundation.layout.Column(
                            modifier = androidx.compose.ui.Modifier.padding(24.dp)
                        ) {
                            androidx.compose.material3.Text("O Mamu não conseguiu iniciar")
                            androidx.compose.material3.Text(startupError)
                            androidx.compose.material3.Text(
                                "Este APK pode não incluir suporte à arquitetura do aparelho. Nenhum recurso nativo será executado até que a compatibilidade seja corrigida."
                            )
                        }
                    }
                }
            }
            return
        }

        setContent {
            MXTheme {"""
    if old_activity in activity:
        activity = activity.replace(old_activity, new_activity, 1)
        if "import androidx.compose.ui.unit.dp" not in activity:
            activity = activity.replace(
                "import androidx.activity.enableEdgeToEdge\n",
                "import androidx.activity.enableEdgeToEdge\nimport androidx.compose.ui.unit.dp\n",
                1
            )
        activity_file.write_text(activity, encoding="utf-8")

    # Fail the build early if upstream changes prevent applying the expected guards.
    checks = {
        "native library guard": "nativeLibraryLoaded = true" in app,
        "no process exit calls": "exitProcess(1)" not in app,
        "search failure guard": "val searchReady = try" in app,
        "pointer failure guard": "val pointerReady = try" in app,
        "startup error screen": "O Mamu não conseguiu iniciar" in activity,
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        raise SystemExit("Compatibilidade inicial não aplicada: " + ", ".join(missing))
    print("Compatibilidade: falhas de inicialização agora exibem diagnóstico em vez de encerrar o processo abruptamente.")

if __name__ == "__main__":
    patch_strings()
    patch_source_phrases()
    patch_startup_compatibility()
