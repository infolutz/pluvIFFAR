# PluvIFFAR - Plataforma de Monitoramento de Precipitação

## Visão Geral

A PluvIFFAR é uma plataforma web completa para monitoramento de precipitação pluviométrica desenvolvida para o Instituto Federal Farroupilha (IFFar). A plataforma permite o cadastro e gerenciamento de estações pluviométricas IoT, coleta automática de dados de precipitação e visualização em tempo real através de gráficos e mapas interativos.

## Funcionalidades Implementadas

### 📊 Área Pública
- **Dashboard Principal**: Visualização em tempo real da precipitação atual
- **Seleção de Localidades**: Lista de estações pluviométricas disponíveis
- **Gráficos Interativos**: Histórico de precipitação em três períodos:
  - Diário (por hora)
  - Mensal (por dia)
  - Anual (por mês)
- **Mapa Interativo**: Visualização geográfica das estações com:
  - Marcadores personalizados
  - Popups informativos
  - Sincronização com seleção de localidade
- **Exportação de Dados**: Funcionalidade de exportação CSV

### 🔐 Área Administrativa
- **Sistema de Autenticação**: Login seguro para administradores
- **Gestão de Dispositivos**: 
  - Cadastro de novas estações pluviométricas
  - Listagem e busca de dispositivos
  - Edição e desativação de estações
  - Validação de campos obrigatórios

### 🌐 API REST
- **Endpoint de Leituras**: `POST /api/v1/readings`
  - Recebe dados dos dispositivos IoT
  - Validação de dispositivos autorizados
  - Armazenamento automático no banco de dados
- **Endpoints de Dados**:
  - `GET /data/locations` - Lista de localidades
  - `GET /data/location/{id}/daily` - Dados diários
  - `GET /data/location/{id}/monthly` - Dados mensais
  - `GET /data/location/{id}/yearly` - Dados anuais
- **Healthcheck**: `GET /api/healthz`

### 🔒 Segurança e Performance
- **Rate Limiting**: 1000 requisições por hora por IP
- **Headers de Segurança**: XSS, CSRF, Content Security Policy
- **CORS Configurado**: Suporte para frontend-backend
- **Middleware de Segurança**: Validação de assinaturas de dispositivos

## Arquitetura Técnica

### Backend (Flask)
- **Framework**: Flask 3.1.1
- **Banco de Dados**: SQLite com SQLAlchemy ORM
- **Segurança**: Flask-Limiter, CORS, headers de segurança
- **Estrutura**:
  ```
  src/
  ├── models/          # Modelos de dados (Device, Reading)
  ├── routes/          # Rotas da API (api, admin, data)
  ├── middleware/      # Middleware de segurança
  ├── static/          # Frontend buildado
  └── main.py          # Aplicação principal
  ```

### Frontend (React)
- **Framework**: React 19.1.0 com Vite
- **UI Components**: Tailwind CSS + shadcn/ui
- **Gráficos**: Chart.js com react-chartjs-2
- **Mapas**: Leaflet com react-leaflet
- **Ícones**: Lucide React
- **Build**: Otimizado para produção

### Modelos de Dados

#### Device (Dispositivo)
```sql
- id: INTEGER (Primary Key)
- device_code: VARCHAR(50) UNIQUE
- mac_address: VARCHAR(17)
- location_name: VARCHAR(200)
- latitude: FLOAT
- longitude: FLOAT
- mm_per_tick_default: FLOAT
- is_active: BOOLEAN
- created_at: DATETIME
```

#### Reading (Leitura)
```sql
- id: INTEGER (Primary Key)
- device_id: INTEGER (Foreign Key)
- timestamp: DATETIME
- ticks: INTEGER
- mm_per_tick: FLOAT
- battery_mv: INTEGER
- created_at: DATETIME
```

## Como Usar

### Para Administradores

1. **Acesso à Área Administrativa**:
   - URL: `http://localhost:5000/admin`
   - Credenciais: `admin` / `admin123`

2. **Cadastro de Dispositivos**:
   - Clique em "Adicionar Dispositivo"
   - Preencha os campos obrigatórios:
     - Código do Dispositivo (ex: ESP001)
     - Endereço MAC (ex: AA:BB:CC:DD:EE:FF)
     - Nome da Localidade
     - Coordenadas (Latitude/Longitude)
     - Calibração (mm por basculamento)

3. **Gestão de Dispositivos**:
   - Use a busca para encontrar dispositivos específicos
   - Botões de ação para editar/desativar dispositivos

### Para Dispositivos IoT

**Envio de Leituras**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Device-Signature: sua-assinatura-aqui" \
  -d '{
    "device_code": "ESP001",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "timestamp": "2025-08-18T10:00:00Z",
    "ticks": 10,
    "mm_per_tick": 0.25,
    "battery_mv": 3300
  }' \
  http://localhost:5000/api/v1/readings
```

### Para Usuários Finais

1. **Visualização de Dados**:
   - Acesse `http://localhost:5000`
   - Selecione uma localidade na sidebar
   - Visualize dados em tempo real no painel central

2. **Análise Histórica**:
   - Use as abas Diário/Mensal/Anual
   - Gráficos interativos com dados agregados
   - Exportação CSV disponível

3. **Localização Geográfica**:
   - Mapa interativo na seção "Localização"
   - Clique nos marcadores para ver detalhes
   - Sincronização com seleção de localidade

## Instalação e Execução

### Requisitos
- Python 3.11+
- Node.js 20+
- pnpm

### Backend
```bash
cd pluviffar_backend
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

### Frontend (Desenvolvimento)
```bash
cd pluviffar_frontend
pnpm install
pnpm run dev
```

### Produção
O frontend já está buildado e integrado ao Flask. Execute apenas:
```bash
cd pluviffar_backend
source venv/bin/activate
python src/main.py
```

## Endpoints da API

### Públicos
- `GET /` - Frontend da aplicação
- `GET /api/healthz` - Status da API
- `GET /data/locations` - Lista de localidades
- `GET /data/location/{id}/daily` - Dados diários
- `GET /data/location/{id}/monthly` - Dados mensais  
- `GET /data/location/{id}/yearly` - Dados anuais

### Dispositivos IoT
- `POST /api/v1/readings` - Envio de leituras

### Administrativos
- `POST /admin/login` - Login de administrador
- `GET /admin/devices` - Lista de dispositivos
- `POST /admin/devices` - Criar dispositivo
- `PUT /admin/devices/{id}` - Atualizar dispositivo
- `DELETE /admin/devices/{id}` - Desativar dispositivo

## Recursos de Segurança

- **Rate Limiting**: Proteção contra ataques de força bruta
- **Headers de Segurança**: Proteção XSS, clickjacking, etc.
- **Validação de Entrada**: Sanitização de dados de entrada
- **Autenticação de Dispositivos**: Assinatura obrigatória para IoT
- **Sessões Seguras**: Gerenciamento seguro de sessões admin

## Status do Projeto

✅ **Completo e Funcional**
- Todas as funcionalidades especificadas foram implementadas
- Frontend e backend totalmente integrados
- Testes realizados e funcionando
- Pronto para implantação em produção

## Tecnologias Utilizadas

**Backend:**
- Flask 3.1.1
- SQLAlchemy (ORM)
- Flask-CORS
- Flask-Limiter

**Frontend:**
- React 19.1.0
- Vite 6.3.5
- Tailwind CSS
- Chart.js
- Leaflet
- Lucide React

**Banco de Dados:**
- SQLite (desenvolvimento)
- Estrutura preparada para PostgreSQL/MySQL (produção)

---

**Desenvolvido para o Instituto Federal Farroupilha (IFFar)**  
*Plataforma de Monitoramento de Precipitação - PluvIFFAR*

