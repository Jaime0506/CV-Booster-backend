# CV Booster

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

## 📋 Descripción del Sistema

**CV Booster** es una aplicación web desarrollada con FastAPI que utiliza inteligencia artificial para optimizar currículums vitae (CVs) para sistemas ATS (Applicant Tracking Systems). El sistema analiza ofertas de trabajo, extrae información clave y adapta el CV del usuario para maximizar las posibilidades de pasar los filtros automáticos de selección.

### 🎯 Características Principales

-   **🤖 Análisis Inteligente de Ofertas**: Extrae automáticamente roles, tecnologías, habilidades y keywords de ofertas de trabajo usando IA
-   **📝 Optimización de CV**: Adapta el CV existente del usuario para incluir keywords relevantes sin inventar información
-   **🔒 Seguridad de Datos**: Ofusca información personal (emails, teléfonos) antes de enviarla a servicios de IA
-   **🔐 Autenticación JWT**: Sistema completo de registro, login y gestión de sesiones con revocación
-   **📄 Procesamiento de Archivos**: Soporte para PDFs y archivos Markdown con validación de tamaño
-   **✅ Validación Post-procesamiento**: Detecta posibles invenciones o métricas no presentes en el CV original
-   **📊 Historial de Uso**: Tracking completo de todas las interacciones con IA por usuario
-   **⚡ Arquitectura Asíncrona**: Base de datos PostgreSQL con SQLAlchemy async para máximo rendimiento

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   PostgreSQL    │
│   (Cliente)     │◄──►│   Backend       │◄──►│   Database      │
│                 │    │                 │    │   (Schema: sys) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OpenRouter    │
                       │   (IA Service)  │
                       │                 |
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Storage       │
                       │   (tmp_jobs/)   │
                       └─────────────────┘
```

### Flujo de Datos

```
1. Usuario → Auth → JWT Token
2. Oferta → IA Analysis → JSON + job_id
3. CV + job_id → Ofuscación → IA → CV Optimizado
4. Validación → Resultado Final
```

### Componentes del Sistema

#### 1. **API Layer (FastAPI)**

-   **main.py**: Punto de entrada de la aplicación
-   **Routers**: Módulos organizados por funcionalidad
    -   `auth/`: Autenticación y gestión de usuarios
    -   `cv_boost/`: Procesamiento y optimización de CVs

#### 2. **Data Layer**

-   **Models**: Definición de entidades de base de datos
    -   `User`: Gestión de usuarios con email normalizado y hash de contraseña
    -   `Session`: Control de sesiones activas con tracking de IP y User-Agent
    -   `LLMUsage`: Historial de uso de IA con tracking de peticiones y resultados
-   **Database**: Configuración de PostgreSQL con SQLAlchemy async y SSL
-   **Schema**: Utiliza el esquema `sys` para organización

#### 3. **Business Logic**

-   **Services**: Lógica de negocio
    -   `ai_client.py`: Integración con OpenRouter/IA con manejo robusto de errores
-   **Utils**: Utilidades auxiliares
    -   `extractor.py`: Extracción de texto de PDFs y Markdown con validación de tamaño
    -   `safety.py`: Ofuscación de datos personales y validación post-procesamiento
    -   `auth_deps.py`: Dependencias de autenticación con validación de sesiones
    -   `jwt_utils.py`: Utilidades JWT con expiración configurable
    -   `llm_tracker.py`: Sistema de tracking para uso de IA

#### 4. **Configuration**

-   **Settings**: Configuración centralizada con Pydantic
-   **Schemes**: Esquemas de validación de datos

## 🔄 Flujo de Funcionamiento

### 1. **Proceso de Autenticación**

```
Usuario → Registro/Login → JWT Token → Sesión Activa
```

### 2. **Proceso de Optimización de CV (2 Pasos)**

#### **Paso A: Análisis de Oferta**

```
Oferta de Trabajo → IA Analysis → JSON Estructurado → Almacenamiento Temporal
```

#### **Paso B: Generación de CV Optimizado**

```
CV Original → Ofuscación → IA Adaptation → Validación → CV Optimizado
```

### 3. **Flujo Detallado**

1. **🔐 Autenticación**: Usuario se registra/hace login → JWT token
2. **📋 Análisis de Oferta**: Usuario sube descripción de trabajo
3. **🤖 IA Analysis**: Sistema analiza con IA y extrae:
    - `rol_detectado`: Posición identificada
    - `seniority`: junior, mid, senior, lead, unknown
    - `tecnologias`: Lista con confianza
    - `skills_duras` y `skills_blandas`
    - `requisitos_imprescindibles` y `requisitos_deseables`
    - `keywords_ats`: Palabras clave priorizadas
    - `suggested_sections`: Secciones recomendadas
    - `confidence_score`: Puntuación de confianza (0-1)
4. **💾 Almacenamiento Temporal**: JSON se guarda con `job_id` único
5. **✏️ Confirmación**: Usuario puede editar keywords antes de continuar
6. **📄 Subida de CV**: Usuario sube CV (PDF/Markdown)
7. **🔒 Ofuscación**: Sistema ofusca emails y teléfonos
8. **🎯 Adaptación IA**: IA adapta CV manteniendo veracidad (Nivel 1)
9. **✅ Validación**: Post-procesamiento detecta posibles invenciones
10. **📤 Resultado**: Retorna CV optimizado en Markdown + metadata

## 🛠️ Tecnologías Utilizadas

### Backend Core

-   **FastAPI 0.117.1**: Framework web moderno con documentación automática
-   **SQLAlchemy 2.0.43**: ORM asíncrono para base de datos
-   **PostgreSQL**: Base de datos relacional con soporte SSL
-   **Pydantic 2.11.9**: Validación de datos y configuración
-   **python-jose 3.5.0**: JWT tokens con algoritmos seguros
-   **bcrypt 5.0.0**: Hash seguro de contraseñas
-   **passlib 1.7.4**: Utilidades de hash de contraseñas

### IA y Procesamiento

-   **OpenRouter**: Servicio de IA con múltiples modelos (x-ai/grok-4-fast:free)
-   **OpenAI SDK 1.109.1**: Cliente oficial para servicios de IA
-   **pdfplumber 0.11.7**: Extracción robusta de texto de PDFs
-   **python-multipart 0.0.20**: Manejo de archivos multipart
-   **pdfminer.six 20250506**: Procesamiento avanzado de PDFs

### Infraestructura y Utilidades

-   **Uvicorn 0.37.0**: Servidor ASGI de alto rendimiento
-   **AsyncPG 0.30.0**: Driver asíncrono nativo para PostgreSQL
-   **python-dotenv 1.1.1**: Gestión de variables de entorno
-   **httpx 0.28.1**: Cliente HTTP asíncrono
-   **email-validator 2.3.0**: Validación de emails

## 📁 Estructura del Proyecto

```
python-ai-proyect/
├── config/                 # Configuración
│   ├── database.py        # Configuración de BD
│   └── settings.py        # Variables de entorno
├── models/                # Modelos de datos
│   ├── user.py           # Modelo de usuario
│   ├── session.py        # Modelo de sesión
│   └── llmUsage.py       # Tracking de uso de IA
├── routers/              # Endpoints de la API
│   ├── auth/            # Autenticación
│   └── cv_boost/        # Optimización de CV
├── services/            # Lógica de negocio
│   └── ai_client.py     # Cliente de IA
├── schemes/             # Esquemas de validación
│   └── schemes.py       # Pydantic models
├── utils/               # Utilidades
│   ├── extractor.py     # Extracción de texto
│   ├── safety.py        # Seguridad y validación
│   ├── auth_deps.py     # Dependencias de auth
│   ├── jwt_utils.py     # Utilidades JWT
│   └── llm_tracker.py   # Tracking de uso de IA
├── storage/             # Almacenamiento temporal
│   └── tmp_jobs/        # Jobs temporales
├── main.py              # Punto de entrada
└── requirements.txt     # Dependencias
```

## 🗄️ Modelo de Datos

### Tablas Principales

#### `sys.users`

```sql
- id: UUID (PK, auto-generado)
- email: TEXT (único)
- email_normalized: TEXT (índice, para búsquedas case-insensitive)
- password_hash: TEXT (bcrypt)
- is_active: BOOLEAN (default: true)
- is_email_confirmed: BOOLEAN (default: true)
- created_at: TIMESTAMP WITH TIME ZONE
- updated_at: TIMESTAMP WITH TIME ZONE
```

#### `sys.sessions`

```sql
- id: UUID (PK, auto-generado)
- user_id: UUID (FK → users.id, CASCADE DELETE)
- created_at: TIMESTAMP WITH TIME ZONE
- last_accessed: TIMESTAMP WITH TIME ZONE
- expires_at: TIMESTAMP WITH TIME ZONE
- user_agent: TEXT
- ip_addr: INET
- is_revoked: BOOLEAN (default: false)
```

#### `sys.llm_usage`

```sql
- id: BIGINT (PK, auto-increment)
- user_id: UUID (FK → users.id, CASCADE DELETE)
- request_id: UUID
- model: TEXT (modelo de IA utilizado)
- endpoint: TEXT (endpoint de la API)
- latency_ms: INTEGER (tiempo de respuesta en ms)
- result: TEXT (resultado generado por la IA)
- created_at: TIMESTAMP WITH TIME ZONE
```

### Almacenamiento Temporal

-   **Directorio**: `storage/tmp_jobs/`
-   **Formato**: Archivos JSON con `job_id.hex`
-   **Contenido**: `job_description` + `extractor_json`
-   **Limpieza**: Manual (se puede implementar TTL automático)

## 🚀 Instrucciones para Levantar en Local

### Prerrequisitos

-   **Python 3.8+** (recomendado 3.11+)
-   **PostgreSQL 12+** con extensión `uuid-ossp`
-   **Cuenta en OpenRouter** (para servicios de IA)
-   **Git** para clonar el repositorio

### 1. **Clonar el Repositorio**

```bash
git clone <tu-repositorio>
cd python-ai-proyect
```

### 2. **Crear Entorno Virtual**

```bash
python -m venv venv

# Windows
./.venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 3. **Instalar Dependencias**

```bash
pip install -r requirements.txt
```

### 4. **Configurar Base de Datos**

#### Crear base de datos PostgreSQL:

```sql
-- Conectar como superusuario
CREATE DATABASE cv_ats_optimizer;
\c cv_ats_optimizer;

-- Crear esquema
CREATE SCHEMA sys;

-- Habilitar extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Configurar variables de entorno:

Crear archivo `.env` en la raíz del proyecto:

```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/cv_ats_optimizer

# JWT - Genera un secret seguro con: openssl rand -hex 32
JWT_SECRET=tu_jwt_secret_muy_seguro_de_64_caracteres_minimo
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenRouter (IA) - Obtén tu API key en: https://openrouter.ai/
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_MODEL=x-ai/grok-4-fast:free

# Almacenamiento
STORAGE_DIR=./storage
MAX_UPLOAD_BYTES=10485760  # 10MB
```

### 5. **Inicializar Base de Datos**

Crear las tablas ejecutando este script Python:

```python
# create_tables.py
import asyncio
from config.database import engine, Base
from models import user, session, llmUsage

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())
```

```bash
python create_tables.py
```

### 6. **Ejecutar la Aplicación**

```bash
# Desarrollo
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 7. **Verificar Instalación**

La aplicación estará disponible en:

-   **API**: http://localhost:8000
-   **Documentación**: http://localhost:8000/docs
-   **ReDoc**: http://localhost:8000/redoc

## 📖 Uso de la API

### 🛠️ Endpoints Disponibles

#### **Autenticación** (`/auth`)

-   `POST /auth/register-user` - Registro de usuario
-   `POST /auth/login-user` - Login de usuario
-   `POST /auth/logout-user` - Logout de usuario
-   `GET /auth/me` - Información del usuario actual

#### **Optimización de CV** (`/cv-boost`)

-   `POST /cv-boost/analyze_job` - Análisis de oferta de trabajo
-   `POST /cv-boost/generate_cv/strict` - Generación de CV optimizado
-   `GET /cv-boost/usage_history` - Historial de uso de IA

### 🔐 Autenticación

#### 1. **Registro de Usuario**

```bash
curl -X POST "http://localhost:8000/auth/register-user" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "mi_password_seguro"
  }'
```

**Respuesta:**

```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@ejemplo.com"
}
```

#### 2. **Login**

```bash
curl -X POST "http://localhost:8000/auth/login-user" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "mi_password_seguro"
  }'
```

**Respuesta:**

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

#### 3. **Verificar Usuario Actual**

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer TU_JWT_TOKEN"
```

### 🤖 Optimización de CV

#### 4. **Análisis de Oferta de Trabajo**

```bash
curl -X POST "http://localhost:8000/cv-boost/analyze_job" \
  -H "Authorization: Bearer TU_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Desarrollador Python Senior con experiencia en FastAPI y PostgreSQL. Requisitos: 5+ años Python, FastAPI, SQLAlchemy, Docker, AWS. Responsabilidades: Desarrollo de APIs, arquitectura de microservicios, liderazgo técnico.",
    "keywords": "Python,FastAPI,PostgreSQL,Docker,AWS"
  }'
```

**Respuesta:**

```json
{
    "job_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "extractor_json": {
        "rol_detectado": "Desarrollador Python Senior",
        "seniority": "senior",
        "tecnologias": [
            { "name": "Python", "confidence": 0.95 },
            { "name": "FastAPI", "confidence": 0.9 },
            { "name": "PostgreSQL", "confidence": 0.85 }
        ],
        "skills_duras": ["Python", "FastAPI", "SQLAlchemy", "Docker", "AWS"],
        "skills_blandas": ["Liderazgo técnico", "Arquitectura"],
        "keywords_ats": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
            "AWS",
            "microservicios"
        ],
        "confidence_score": 0.88
    },
    "message": "Análisis generado. Muestra esto al usuario y pídeles confirmar/editar keywords antes de generar el CV."
}
```

#### 5. **Generación de CV Optimizado**

```bash
curl -X POST "http://localhost:8000/cv-boost/generate_cv/strict" \
  -H "Authorization: Bearer TU_JWT_TOKEN" \
  -F "job_id=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -F "cv=@mi_cv.pdf" \
  -F "confirm_keywords=Python,FastAPI,PostgreSQL,Docker,AWS,Microservicios"
```

**Nota**: Este endpoint requiere `form-data` porque incluye archivos.

**Respuesta:**

```json
{
    "extractor_json": {
        /* JSON del análisis */
    },
    "cv_markdown": "# Juan Pérez\n\n## Desarrollador Python Senior\n\n### Experiencia\n- 5+ años desarrollando APIs con **Python** y **FastAPI**\n- Arquitectura de **microservicios** en **AWS**\n- Liderazgo técnico en equipos de desarrollo\n\n### Habilidades Técnicas\n- **Python** (Avanzado)\n- **FastAPI** (Experto)\n- **PostgreSQL** (Avanzado)\n- **Docker** (Intermedio)\n- **AWS** (Intermedio)",
    "postprocess_checks": {
        "new_lines": [],
        "suspicious_metrics": []
    },
    "obfuscation_mapping": {
        "emails": ["juan.perez@email.com"],
        "phones": ["+34 600 123 456"]
    }
}
```

### 🔄 Logout

```bash
curl -X POST "http://localhost:8000/auth/logout-user" \
  -H "Authorization: Bearer TU_JWT_TOKEN"
```

#### 6. **Historial de Uso de IA**

```bash
curl -X GET "http://localhost:8000/cv-boost/usage_history?limit=10&offset=0" \
  -H "Authorization: Bearer TU_JWT_TOKEN"
```

**Respuesta:**

```json
{
    "history": [
        {
            "id": 1,
            "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "model": "x-ai/grok-4-fast:free",
            "endpoint": "/cv-boost/analyze_job",
            "latency_ms": 1250,
            "result_preview": "{\n  \"rol_detectado\": \"Desarrollador Python Senior\",\n  \"seniority\": \"senior\",\n  \"tecnologias\": [\n    {\"name\": \"Python\", \"confidence\": 0.95}\n  ]...",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total_returned": 1,
    "limit": 10,
    "offset": 0
}
```

## 🔒 Seguridad

-   **Ofuscación de Datos**: Emails y teléfonos se ofuscan antes de enviar a IA
-   **Validación Post-procesamiento**: Detecta posibles invenciones
-   **Autenticación JWT**: Tokens seguros con expiración
-   **Gestión de Sesiones**: Control de sesiones activas y revocación
-   **Validación de Archivos**: Límites de tamaño y tipos permitidos
-   **Tracking de Uso**: Registro completo de todas las interacciones con IA

## 🧪 Testing

Para probar la funcionalidad:

1. **Registra un usuario** usando el endpoint `/auth/register-user`
2. **Haz login** y obtén el token JWT
3. **Analiza una oferta** con `/cv-boost/analyze_job` (acepta JSON)
4. **Sube tu CV** y genera la versión optimizada con `/cv-boost/generate_cv/strict`
5. **Consulta tu historial** con `/cv-boost/usage_history`

## 📊 Monitoreo

El sistema incluye tracking de uso de IA en la tabla `llm_usage` para:

-   Monitorear costos
-   Analizar rendimiento
-   Detectar problemas

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Troubleshooting

### Problemas Comunes

#### ❌ Error de Conexión a Base de Datos

```bash
# Verificar que PostgreSQL esté ejecutándose
sudo systemctl status postgresql

# Verificar conexión
psql -h localhost -U usuario -d cv_ats_optimizer
```

#### ❌ Error de Variables de Entorno

```bash
# Verificar que el archivo .env existe
ls -la .env

# Verificar variables cargadas
python -c "from config.settings import settings; print(settings.DATABASE_URL)"
```

#### ❌ Error de OpenRouter API

```bash
# Verificar API key
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models
```

#### ❌ Error de Permisos de Archivos

```bash
# Crear directorio de storage
mkdir -p storage/tmp_jobs
chmod 755 storage/tmp_jobs
```

### Logs y Debugging

#### Ver logs de la aplicación:

```bash
# Con uvicorn en modo debug
uvicorn main:app --reload --log-level debug
```

#### Verificar tablas creadas:

```sql
\c cv_ats_optimizer
\dt sys.*

-- Verificar estructura de llm_usage
\d sys.llm_usage

-- Verificar datos de tracking
SELECT COUNT(*) FROM sys.llm_usage;
```

### Performance

-   **Base de datos**: Usa índices en `email_normalized`, `user_id` y `created_at`
-   **Archivos temporales**: Limpia `storage/tmp_jobs/` periódicamente
-   **Tokens JWT**: Ajusta `ACCESS_TOKEN_EXPIRE_MINUTES` según necesidades
-   **Historial de IA**: Considera implementar limpieza automática de registros antiguos

## 📊 Métricas y Monitoreo

### Endpoints de Monitoreo

-   **Health Check**: `GET /` - Estado básico de la API
-   **Documentación**: `GET /docs` - Swagger UI interactivo
-   **ReDoc**: `GET /redoc` - Documentación alternativa

### Tracking de Uso

El sistema registra automáticamente en `sys.llm_usage`:

-   **Usuario**: ID del usuario que realizó la petición
-   **Request ID**: Identificador único de cada petición
-   **Modelo**: Modelo de IA utilizado (ej: x-ai/grok-4-fast:free)
-   **Endpoint**: Endpoint de la API llamado
-   **Latencia**: Tiempo de respuesta en milisegundos
-   **Resultado**: Texto completo generado por la IA
-   **Timestamp**: Fecha y hora de la petición

#### Endpoint de Historial

-   **GET** `/cv-boost/usage_history` - Consultar historial de uso del usuario

## 🚀 Despliegue en Producción

### Variables de Entorno Adicionales

```env
# Producción
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/cv_ats_optimizer
JWT_SECRET=secret_super_seguro_de_produccion
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=tu_sentry_dsn_si_usas_monitoreo
```

### Docker (Opcional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contribución

### Cómo Contribuir

1. **Fork** el repositorio
2. **Crea una rama** para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abre un Pull Request**

### Estándares de Código

-   Usa **type hints** en todas las funciones
-   Sigue **PEP 8** para estilo de código
-   Añade **docstrings** para funciones públicas
-   Incluye **tests** para nuevas funcionalidades

## 📝 Licencia

Este proyecto está bajo la **Licencia MIT**. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes problemas o preguntas:

1. 📖 Revisa la documentación de la API en `/docs`
2. 🔍 Verifica los logs de la aplicación
3. ⚙️ Asegúrate de que todas las variables de entorno estén configuradas
4. 🗄️ Comprueba la conexión a la base de datos
5. 🐛 Revisa la sección de [Troubleshooting](#-troubleshooting)

---

**Desarrollado con ❤️ usando FastAPI, PostgreSQL y IA**

_Optimiza tu CV y consigue el trabajo de tus sueños_ 🚀
