# ClimateTest Manager v0.6.1

Correção de implantação focada em confiabilidade do instalador do servidor central.

- valida o servidor local antes de considerar a instalação pronta;
- mantém os dados em `C:\ProgramData\ClimateTestManager\Data`;
- preserva instalações anteriores e backups durante atualização;
- registra diagnóstico em `C:\ProgramData\ClimateTestManager\Logs`;
- usa fallback de inicialização quando o Agendador de Tarefas não puder registrar o servidor;
- limita a regra de firewall à sub-rede local;
- evita abertura automática do cliente quando o servidor não foi validado;
- evita travamento na reconexão e mostra códigos CTM-SRV/CTM-CLI compreensíveis.

O banco de dados não é removido na desinstalação.
