# Task #11: Model Parameters Data Flow

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OLLAMA API                                    │
│                   http://localhost:11434/api/tags                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ GET request
                             │
                             ▼
                    ┌─────────────────┐
                    │  Raw Response   │
                    │  {              │
                    │    "models": [  │
                    │      {          │
                    │        "details": {              │
                    │          "parameter_size": "3.2B"│  ◄─── Source
                    │        }        │                │
                    │      }          │                │
                    │    ]            │                │
                    │  }              │                │
                    └────────┬────────┘                │
                             │                         │
                             │ Extract                 │
                             │                         │
                             ▼                         │
┌─────────────────────────────────────────────────────────────────────┤
│                     BACKEND API                                      │
│            agentos/webui/api/models.py                              │
│                                                                      │
│  1. list_models() method (line 224-236)                            │
│     ┌────────────────────────────────────────┐                     │
│     │ # Extract parameter size               │                     │
│     │ parameter_size = model.get("details",  │                     │
│     │   {}).get("parameter_size")            │  ◄─── Extract       │
│     │                                        │                     │
│     │ models.append(ModelInfo(               │                     │
│     │   ...                                  │                     │
│     │   parameters=parameter_size  ◄──────────────── Map          │
│     │ ))                                     │                     │
│     └────────────────────────────────────────┘                     │
│                                                                      │
│  2. ModelInfo class (line 89-97)                                   │
│     ┌────────────────────────────────────────┐                     │
│     │ class ModelInfo(BaseModel):            │                     │
│     │   name: str                            │                     │
│     │   provider: str = "ollama"             │                     │
│     │   ...                                  │                     │
│     │   parameters: Optional[str] = None ◄────────── Define        │
│     └────────────────────────────────────────┘                     │
│                                                                      │
│  3. API Response                                                    │
│     http://localhost:8188/api/models/list                          │
│     {                                                                │
│       "models": [{                                                   │
│         "name": "llama3.2:3b",                                      │
│         "parameters": "3.2B"  ◄───────────────────── Output        │
│       }]                                                             │
│     }                                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP Response
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND UI                                     │
│         agentos/webui/static/js/views/ModelsView.js                 │
│                                                                      │
│  1. renderModelCard() (line 321)                                   │
│     ┌────────────────────────────────────────┐                     │
│     │ const paramsText =                     │                     │
│     │   model.parameters ||  ◄────────────────────── Use           │
│     │   model.parameter_size ||              │                     │
│     │   'Unknown';                           │                     │
│     └────────────────────────────────────────┘                     │
│                          │                                          │
│                          │ Display                                  │
│                          ▼                                          │
│     ┌────────────────────────────────────────┐                     │
│     │  Model Card                            │                     │
│     │  ┌──────────────────────────────────┐  │                     │
│     │  │ llama3.2:3b                      │  │                     │
│     │  │ Size: 2.0 GB                     │  │                     │
│     │  │ Parameters: 3.2B  ◄────────────────────── Display         │
│     │  └──────────────────────────────────┘  │                     │
│     └────────────────────────────────────────┘                     │
│                                                                      │
│  2. showModelInfo() (line 745)                                     │
│     ┌────────────────────────────────────────┐                     │
│     │  Info Modal                            │                     │
│     │  ┌──────────────────────────────────┐  │                     │
│     │  │ Parameters: 3.2B  ◄─────────────────────── Display        │
│     │  └──────────────────────────────────┘  │                     │
│     └────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Points

1. **Data Source**: Ollama API provides `parameter_size` in the `details` object
2. **Backend Processing**: Extracts and maps to `parameters` field in ModelInfo
3. **API Exposure**: Returns `parameters` in JSON response
4. **Frontend Display**: Uses `model.parameters` with fallback to `model.parameter_size`

## Example Values

| Model Name      | Parameter Size | Display     |
|----------------|----------------|-------------|
| llama3.2:3b    | "3.2B"        | 3.2B        |
| llama3.2:1b    | "1.3B"        | 1.3B        |
| qwen2.5:7b     | "7B"          | 7B          |
| gemma2:2b      | "2B"          | 2B          |
| Not available  | null          | Unknown     |

## Backward Compatibility

The frontend checks both field names for compatibility:
```javascript
model.parameters || model.parameter_size || 'Unknown'
```

This ensures the UI works with:
- New API (returns `parameters`)
- Old API (returns `parameter_size`)
- Missing data (shows `Unknown`)
