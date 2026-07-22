# Regras de negócio

## Fonte normativa

- Norma informada pelo laboratório: **ABNT NBR IEC 60079-0:2020**.
- Referência utilizada nesta etapa: Tabela 17 fornecida para o projeto.
- Cálculo da temperatura de serviço: `Ts = Tamb máxima + ΔT máximo`.
- Quando o cliente não informar a Tamb máxima, adotar `+40 °C`, conforme a Tabela 1 da
  ABNT NBR IEC 60079-0:2020.

O formulário deve informar explicitamente quando `+40 °C` estiver sendo adotado. O valor efetivo
deve ser persistido no ensaio e a origem desse valor deve constar no evento inicial de auditoria.

## Dados do cadastro

- A determinação da condição climática utiliza o EPL; a Marcação Ex não é solicitada.
- O processo é um identificador obrigatório de conteúdo livre, limitado a 10 caracteres na tela.
- Tamb e Delta T aceitam somente conteúdo numérico, com vírgula como separador visual.
- Um ponto digitado como separador decimal deve ser convertido imediatamente para vírgula.
- As permanências devem exibir horas, dias nominais e o limite superior incluindo a tolerância.

Os valores calculados deverão ser armazenados como fotografia da regra usada no cadastro.
Uma atualização futura da norma não deverá alterar retroativamente ensaios já registrados.

## Grupos de EPL

| Grupo | EPLs |
| --- | --- |
| Grupo 1 | Ga, Gb, Da, Db, Ma e Mb |
| Grupo 2 | Gc e Dc |

## Grupo 1 — Ga, Gb, Da, Db, Ma e Mb

| Faixa de Ts | Opção | Câmara climática | Secagem |
| --- | --- | --- | --- |
| `Ts ≤ 70 °C` | A | 672 h; 90 ± 5% UR; `máx(Ts + 20 K, 80 °C) ± 2 K` | Não aplicável |
| `70 °C < Ts < 75 °C` | A | 672 h; 90 ± 5% UR; `Ts + 20 K ± 2 K` | Não aplicável |
| `70 °C < Ts < 75 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |
| `Ts ≥ 75 °C` | A | 336 h; 90 ± 5% UR; `95 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |
| `Ts ≥ 75 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 20 K ± 2 K` |

### Interpretação de Ts igual a 75 °C

Por orientação do laboratório, `Ts = 75 °C` utiliza as condições apresentadas na linha
`Ts > 75 °C`. No código, isso é representado explicitamente como `Ts ≥ 75 °C`.

## Grupo 2 — Gc e Dc

| Faixa de Ts | Opção | Câmara climática | Secagem |
| --- | --- | --- | --- |
| `Ts ≤ 80 °C` | A | 672 h; 90 ± 5% UR; `Ts + 10 K ± 2 K` | Não aplicável |
| `80 °C < Ts ≤ 85 °C` | A | 672 h; 90 ± 5% UR; `Ts + 10 K ± 2 K` | Não aplicável |
| `80 °C < Ts ≤ 85 °C` | B | 336 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |
| `Ts > 85 °C` | A | 336 h; 90 ± 5% UR; `95 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |
| `Ts > 85 °C` | B | 504 h; 90 ± 5% UR; `90 °C ± 2 K` | 336 h; `Ts + 10 K ± 2 K` |

Para Gc e Dc, não é aplicado o mínimo de 80 °C que aparece na primeira faixa do Grupo 1.

## Tolerâncias

- Temperatura da câmara e da secagem: `± 2 K`.
- Umidade relativa: `90 ± 5% UR`.
- Cada período indicado em horas possui tolerância de `+30/0 h`.

O sistema deverá manter separados:

- horário nominal de saída;
- horário máximo permitido;
- horário real registrado pelo operador.

Quando houver secagem, a saída deverá ser recalculada a partir do início real dessa etapa.

## Situação e condição

Situação descreve onde o ensaio está no fluxo:

- Aguardando
- Na Câmara
- Em Secagem
- Finalizado
- Cancelado

Condição descreve o prazo da próxima ação necessária:

- No prazo
- Vence hoje
- Atrasado
