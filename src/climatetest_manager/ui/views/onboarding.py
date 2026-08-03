"""Central de ajuda orientada às tarefas reais do laboratório."""

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from climatetest_manager.ui.components import dialog_banner, styled_dialog
from climatetest_manager.ui.email_help import EMAIL_SETUP_STEPS
from climatetest_manager.ui.theme import AppColors


@dataclass(frozen=True, slots=True)
class HelpTopic:
    icon: ft.IconData
    title: str
    summary: str
    steps: tuple[str, ...]


TOPICS = (
    HelpTopic(
        ft.Icons.ADD_TASK,
        "Como cadastrar um novo ensaio",
        "Preencha a identificação e escolha como a condição térmica foi definida.",
        (
            "Abra “Novo ensaio” no menu lateral.",
            "Informe cliente, processo, produto e quantidade de amostras.",
            "Escolha Tamb + ΔT, Ts informado ou Personalizado.",
            "Confira a condição calculada e clique em “Salvar ensaio”.",
        ),
    ),
    HelpTopic(
        ft.Icons.EDIT_NOTE,
        "Como editar um ensaio cadastrado",
        "Corrija informações mantendo o motivo e os valores anteriores no histórico.",
        (
            "Abra o ensaio pela lista, Agenda ou Dashboard.",
            "Clique em “Corrigir dados”.",
            "Altere somente as informações necessárias.",
            "Selecione o motivo; use “Outros” somente se nenhuma opção representar o caso.",
            "Confira e salve. Os valores anterior e novo ficarão no registro técnico.",
        ),
    ),
    HelpTopic(
        ft.Icons.PLAY_CIRCLE_OUTLINE,
        "Como registrar entrada e retirada",
        "Registre o horário real e confira a retirada nominal antes de confirmar.",
        (
            "Abra os detalhes do ensaio.",
            "Use “Registrar agora” se a operação estiver acontecendo neste momento.",
            "Use o horário manual somente se a operação já aconteceu.",
            "Confira a data nominal e o limite mostrados na confirmação.",
            "Para corrigir, use “Corrigir horários” e escolha exatamente entrada ou saída da "
            "câmara climática ou da câmara seca.",
        ),
    ),
    HelpTopic(
        ft.Icons.CANCEL_OUTLINED,
        "Como cancelar ou excluir um ensaio",
        "Cancelamento preserva o histórico; exclusão só existe antes do início.",
        (
            "Use “Cancelar ensaio” quando a execução já começou.",
            "Selecione o motivo do cancelamento ou escolha “Outros” para uma descrição breve.",
            "Use “Excluir cadastro” apenas para um ensaio que ainda aguarda início.",
            "Confirme a ação somente depois de conferir processo e cliente.",
        ),
    ),
    HelpTopic(
        ft.Icons.PAUSE_CIRCLE_OUTLINE,
        "Como pausar ou retomar a câmara",
        "A pausa global congela os prazos de todos os ensaios afetados.",
        (
            "No Dashboard, localize o cartão da câmara ou da secagem.",
            "Clique em “Pausar” e selecione o motivo da indisponibilidade.",
            "Enquanto pausado, nenhuma etapa afetada poderá avançar.",
            "Clique em “Retomar” quando o equipamento voltar a operar.",
        ),
    ),
    HelpTopic(
        ft.Icons.MANAGE_ACCOUNTS_OUTLINED,
        "Como cadastrar um novo usuário",
        "Somente administradores podem criar contas para pessoas autorizadas.",
        (
            "Abra “Usuários” no menu lateral.",
            "Clique em “Novo usuário”.",
            "Informe nome, usuário, e-mail, senha inicial e perfil.",
            "O usuário poderá trocar a própria senha em Configurações.",
        ),
    ),
    HelpTopic(
        ft.Icons.MARK_EMAIL_READ_OUTLINED,
        "Como configurar avisos por e-mail",
        "Configure uma conta SMTP, teste o envio e ative a verificação em segundo plano.",
        EMAIL_SETUP_STEPS,
    ),
    HelpTopic(
        ft.Icons.BACKUP,
        "Como proteger o banco de dados",
        "Mantenha o banco local e envie somente cópias consistentes ao OneDrive.",
        (
            "Na primeira abertura, escolha uma pasta local estável para o banco ativo.",
            "Escolha uma pasta do OneDrive para receber uma segunda cópia diária.",
            "Em Configurações, confira os dois caminhos na seção Local dos dados.",
            "Somente administradores podem usar Alterar pasta de backup.",
            "Nunca mova o arquivo climatetest_manager.db aberto para uma pasta sincronizada.",
        ),
    ),
)

# Mantém o nome público antigo para extensões e testes que importavam STEPS.
STEPS = TOPICS


class OnboardingView:
    """Apresenta perguntas práticas em vez de um tutorial obrigatório longo."""

    def __init__(
        self,
        *,
        user_name: str,
        on_complete: Callable[[], None],
        first_access: bool,
    ) -> None:
        self._on_complete = on_complete
        self._first_access = first_access
        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=10,
                    controls=[
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(
                                    (f"Bem-vindo, {user_name}" if first_access else "Guia de uso"),
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Escolha o que você precisa fazer no sistema.",
                                    size=14,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Button(
                            content="Começar a usar" if first_access else "Fechar guia",
                            icon=ft.Icons.CHECK if first_access else ft.Icons.CLOSE,
                            bgcolor=AppColors.PRIMARY if first_access else None,
                            color=AppColors.WHITE if first_access else AppColors.PRIMARY,
                            on_click=lambda _event: self._on_complete(),
                        ),
                    ],
                ),
                *(
                    [
                        ft.Container(
                            border_radius=14,
                            bgcolor=AppColors.INFO_LIGHT,
                            padding=16,
                            content=ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.HELP_OUTLINE,
                                        color=AppColors.INFO,
                                    ),
                                    ft.Text(
                                        "Você não precisa memorizar este guia. Passe o "
                                        "ponteiro sobre os ícones “?” das telas para ver "
                                        "explicações rápidas.",
                                        size=12,
                                        color=AppColors.TEXT_PRIMARY,
                                        expand=True,
                                    ),
                                ],
                            ),
                        )
                    ]
                    if first_access
                    else []
                ),
                *[self._topic_card(topic) for topic in TOPICS],
                ft.Container(height=8),
            ],
        )

    def _topic_card(self, topic: HelpTopic) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=15,
            padding=18,
            tooltip="Clique para abrir o passo a passo",
            on_click=lambda _event, selected=topic: self._show_topic(selected),
            content=ft.Row(
                spacing=15,
                controls=[
                    ft.Container(
                        width=46,
                        height=46,
                        border_radius=13,
                        bgcolor=AppColors.PRIMARY_LIGHT,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(topic.icon, color=AppColors.PRIMARY),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=3,
                        controls=[
                            ft.Text(
                                topic.title,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                topic.summary,
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
        )

    def _show_topic(self, topic: HelpTopic) -> None:
        page = self.root.page
        page.show_dialog(
            styled_dialog(
                title=topic.title,
                subtitle="Guia de uso do ClimateTest Manager",
                icon=topic.icon,
                scrollable=True,
                content=ft.Column(
                    width=560,
                    tight=True,
                    spacing=12,
                    controls=[
                        dialog_banner(topic.summary),
                        *[
                            ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Container(
                                        width=26,
                                        height=26,
                                        border_radius=13,
                                        bgcolor=AppColors.PRIMARY_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(
                                            str(index),
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.PRIMARY,
                                        ),
                                    ),
                                    ft.Text(step, size=13, expand=True),
                                ],
                            )
                            for index, step in enumerate(topic.steps, start=1)
                        ],
                    ],
                ),
                actions=[
                    ft.Button(
                        content="Entendi",
                        icon=ft.Icons.CHECK,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        on_click=lambda _event: page.pop_dialog(),
                    )
                ],
            )
        )


def build_onboarding_view(
    *,
    user_name: str,
    on_complete: Callable[[], None],
    first_access: bool,
) -> ft.Column:
    return OnboardingView(
        user_name=user_name,
        on_complete=on_complete,
        first_access=first_access,
    ).root
