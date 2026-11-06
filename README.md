# PluvIFFar — execução local

Plataforma reconstruída para receber leituras de pluviômetros, visualizar chuva por estação e gerenciar dispositivos. Backend Flask + SQLite e frontend HTML/CSS/JavaScript servido pelo próprio Flask. **Não precisa de Node, npm ou pnpm.**

## Requisitos

Python 3.11 ou superior com pip e venv. Internet é necessária para instalar dependências e para carregar o mapa OpenStreetMap. O painel e os gráficos funcionam sem serviço de terceiros.

## Windows (PowerShell)

Abra o terminal na pasta extraída que contém este README:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Não é necessário ativar o ambiente virtual nem alterar a política de execução do PowerShell.

## Linux / macOS

Abra o terminal na pasta extraída que contém este README:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Em distribuições Linux que não incluam venv, instale o pacote `python3-venv` pelo gerenciador do sistema.

## Abrir no navegador

- Painel: http://127.0.0.1:5000
- Administração: http://127.0.0.1:5000/admin
- Saúde da API: http://127.0.0.1:5000/api/healthz

No primeiro início, o terminal mostra o usuário `admin` e uma **senha gerada automaticamente**. Guarde essa senha: ela não será exibida novamente. Seu hash fica no SQLite. Para definir ou redefinir a senha, configure `ADMIN_PASS` antes de iniciar. Pare com Ctrl+C.

O servidor escuta somente em 127.0.0.1, no seu computador. Um ambiente remoto tem seu próprio localhost; baixe o ZIP e execute no computador em que você vai abrir o navegador.

## Configuração opcional

Variáveis de ambiente reconhecidas (o arquivo `.env` não é carregado automaticamente):

| Variável | Uso |
| --- | --- |
| `ADMIN_USER` | Nome de usuário; padrão `admin` |
| `ADMIN_PASS` | Define a senha administrativa durante essa execução |
| `SECRET_KEY` | Chave de sessão; sem ela, sessões expiram ao reiniciar |
| `DATABASE_PATH` | Caminho para SQLite; padrão `pluviffar_backend/instance/pluviffar.sqlite3` |
| `PORT` | Porta local; padrão `5000` |
| `DEFAULT_LATITUDE` / `DEFAULT_LONGITUDE` | Coordenadas da estação inicial, somente na criação do banco |

Exemplo PowerShell:

```powershell
$env:ADMIN_PASS = "escolha-uma-senha-forte"
.\.venv\Scripts\python.exe main.py
```

Linux / macOS:

```bash
ADMIN_PASS='escolha-uma-senha-forte' .venv/bin/python main.py
```

Não apague o banco para redefinir a senha: isso apagaria as leituras. Faça backup do arquivo SQLite com o servidor parado.

## Primeira estação e envio de leitura

O banco inicia com **IFFar – Campus Panambi**, código `ESP001`, MAC `84:CC:A8:12:34:56` e calibração de `0.25 mm`. As coordenadas iniciais são aproximadas; edite-as em `/admin`. Não há leituras fictícias pré-carregadas.

Com o servidor ligado, execute em outro terminal, usando o Python do ambiente virtual (no Windows substitua `.venv/bin/python` por `.\.venv\Scripts\python.exe`):

```bash
.venv/bin/python examples/send_reading.py
```

Esse exemplo envia uma **leitura de teste de 1 mm** à estação inicial e altera o banco. Ela aparecerá no painel após atualizar a página. Use somente para testar, antes de conectar dispositivos reais. Para dados reais, cadastre os códigos e MACs dos seus ESP8266 em `/admin`.

Payload da API `POST /api/v1/readings`:

```json
{
  "device_code": "ESP001",
  "mac_address": "84:CC:A8:12:34:56",
  "timestamp": "2026-01-01T12:00:00Z",
  "ticks": 4,
  "mm_per_tick": 0.25,
  "battery_mv": 3850
}
```

`timestamp` precisa incluir fuso horário. `ticks` é inteiro não negativo e representa basculamentos **do intervalo**, não um contador acumulado desde que o dispositivo ligou. `mm_per_tick` e `battery_mv` são opcionais. A calibração do cadastro é usada quando omitida.

Resposta inicial: HTTP 201, `stored: true`. Reenvio do mesmo timestamp e conteúdo: HTTP 200, `stored: false`. Mesmo timestamp com conteúdo diferente: HTTP 409. Dispositivo inativo ou credenciais incorretas: HTTP 401. Payload inválido: HTTP 422.

## O que está implementado

- Busca de localidades, seleção de estação e total de hoje.
- Histórico diário por hora, mensal por dia e anual por mês, com data selecionável.
- Gráfico SVG, tabela e exportação CSV do período selecionado.
- Datas consolidadas em `America/Sao_Paulo`, incluindo viradas de dia/mês/ano.
- Marcador da estação no OpenStreetMap; o mapa requer internet.
- Login administrativo por sessão, proteção CSRF e limite de tentativas.
- Cadastro, edição, busca, desativação e reativação de dispositivos.
- Auditoria das alterações de dispositivos.
- Ingestão validada, limite de 1.000 requisições/hora por IP e prevenção de leituras duplicadas.
- Banco SQLite persistente e estação padrão sem dados simulados.

Não há opção de login no painel público; acesse `/admin` diretamente. Os intervalos sem dados somam zero, mas isso **não confirma ausência de chuva**: a estação pode não ter enviado dados.

A autenticação dos dispositivos segue o código + MAC do requisito original; não implementa assinatura criptográfica. Esta versão é para execução local. Antes de exposição à internet, planeje HTTPS, autenticação forte por dispositivo e servidor de produção. Limites de requisições são locais ao processo e reiniciam com o servidor.

## Estrutura

```text
main.py                       # inicia o servidor local
requirements.txt              # dependências
pluviffar_backend/app.py       # aplicação, API, autenticação e banco
pluviffar_frontend/index.html  # interface
pluviffar_frontend/style.css
pluviffar_frontend/app.js
examples/send_reading.py       # envio manual de teste
tests/test_app.py              # testes de integração
docs/arquivos-originais/       # arquivos anteriores preservados como referência
```

Os arquivos originais incompletos e a documentação antiga estão em `docs/arquivos-originais`; eles não são usados na aplicação reconstruída.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

No Windows use `.\.venv\Scripts\python.exe`. Os testes usam bancos temporários e não alteram seus dados locais.
