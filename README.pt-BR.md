# astrbot_dw_ext_br_south_disaster

[English](README.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | [日本語](README.ja-JP.md)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/h0ffmann/astrbot_dw_ext_br_south_disaster)

> Este texto é uma tradução. Em caso de diferença, vale a [versão em inglês](README.md).

Esta extensão funciona com o plugin do AstrBot [astrbot_plugin_disaster_warning](https://github.com/Pancakes-Labs/astrbot_plugin_disaster_warning).
A extensão envia alertas do CEMADEN de chuva, inundação e deslizamento para o Sul do Brasil (RS, SC e PR).
A extensão acrescenta às mensagens dados de El Niño e La Niña da NOAA CPC.

> [!WARNING]
> Os dados servem apenas como referência. Os dados não são um alerta oficial. Siga sempre as instruções da Defesa Civil e das autoridades locais.

> [!CAUTION]
> A extensão executa código Python no mesmo processo do host. A instalação concede à extensão acesso ao host e aos dados do host.

## Documentação

A [wiki](https://github.com/h0ffmann/astrbot_dw_ext_br_south_disaster/wiki) tem mais informações nos mesmos idiomas.

## Requisitos

- O host deve ter o sistema de extensões. Nenhuma versão publicada do host tem esse sistema.
- A versão do host deve ser 1.6.5 ou superior.

## Instalação

O fluxo de instalação do host ainda não está disponível. Siga estes passos para instalar manualmente:

1. Abra o diretório de dados do plugin. Crie o diretório `extensions` se ele não existir.
2. Coloque este repositório em `extensions/br_south_disaster`. O nome do diretório deve ser igual ao id da extensão.
3. Adicione `br_south_disaster` a `extensions.enabled_ids` na configuração do plugin.
4. Recarregue o plugin.

## Configuração

Coloque as opções em `extensions.settings`. O valor é um texto JSON:

```json
{
  "enabled_ids": ["br_south_disaster"],
  "settings": "{\"br_south_disaster\": {\"language\": \"en\", \"rain_interval\": 600}}"
}
```

## Opções

| Opção | Padrão | Descrição |
| :--- | :--- | :--- |
| `language` | `zh-CN` | O idioma das mensagens. Os valores são `zh-CN`, `en`, `pt-BR` e `ja-JP`. |
| `alerts_interval` | `300` | O tempo entre duas consultas aos alertas do CEMADEN, em segundos. |
| `rain_interval` | `300` | O tempo entre duas consultas aos pluviômetros do CEMADEN, em segundos. |
| `states` | `["RS", "SC", "PR"]` | A lista de estados monitorados. A extensão ignora um código desconhecido. Se nenhum código for conhecido, a extensão usa todos os estados e registra um aviso. |
| `rain_thresholds` | Veja abaixo | Os totais de chuva que definem o nível de um alerta de pluviômetro. |

`rain_thresholds` tem três chaves: `yellow`, `orange` e `red`. Cada chave tem `acc1hr` (chuva na última 1 hora, em mm) e `acc24hr` (chuva nas últimas 24 horas, em mm). Um pluviômetro atinge um nível quando um dos dois valores alcança o limiar. Uma chave omitida mantém o valor padrão.

| Chave | Nível | `acc1hr` (mm) | `acc24hr` (mm) |
| :--- | :--- | :--- | :--- |
| `yellow` | 2 | 20 | 50 |
| `orange` | 3 | 30 | 100 |
| `red` | 4 | 60 | 150 |

Para adicionar um estado, adicione uma linha a `states.py`.

## Fontes de dados

| Fonte | Dados | Frequência de atualização |
| :--- | :--- | :--- |
| [Alertas do CEMADEN](docs/CEMADEN%20API.md) | Alertas de risco de cada município | A extensão lê os dados a cada `alerts_interval` |
| [Pluviômetros do CEMADEN](docs/CEMADEN%20API.md) | Totais de chuva de cada pluviômetro, com uma consulta para cada estado | A extensão lê os dados a cada `rain_interval` |
| [NOAA CPC ONI](docs/NOAA%20CPC%20ONI.md) | O Índice Oceânico do Niño | A NOAA publica um novo valor por mês |

O levantamento das fontes brasileiras está em [docs/brazil-sources-survey.md](docs/brazil-sources-survey.md). Os documentos em `docs/` estão em inglês.

## Desenvolvimento

Os testes usam as classes reais do host. O comando `just setup` baixa uma cópia fixa do host em `.host/`.
Você precisa de [just](https://github.com/casey/just) e [uv](https://github.com/astral-sh/uv). Com Nix, o comando `nix develop` fornece essas ferramentas.

```sh
just setup
just check
```

O comando `just check` executa as verificações de formato, regras de código, tipos, complexidade e testes. A CI executa o mesmo comando.
Execute `just` para ver todos os comandos. O comando `just live` executa os testes que consultam os serviços reais do CEMADEN e da NOAA CPC.
Defina `DW_HOST_DIR` para usar outra cópia do host.

## Regras de escrita

Escreva o texto em inglês em ASD-STE100 Simplified Technical English. A skill incluída neste repositório está em `.claude/skills/asd-ste100`.
Este comando verifica um arquivo:

```sh
python3 .claude/skills/asd-ste100/scripts/ste-lint.py README.md
```

## Licença

O código está sob a [Mozilla Public License 2.0](LICENSE). O arquivo `extension.png` está sob CC-BY-4.0. Consulte `meta.json`.
Os arquivos em `.claude/skills/asd-ste100` estão sob a licença MIT. Consulte `.claude/skills/asd-ste100/LICENSE`.
