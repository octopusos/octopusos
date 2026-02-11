# API Contracts

## Contract SoT
- Runtime FastAPI OpenAPI from the fully mounted contract app is the only contract source of truth.
- Snapshot path: `outputs/contracts/openapi.snapshot.json`
- Snapshot checksum: `outputs/contracts/openapi.snapshot.sha256`

## Generation Flow
1. Export snapshot from backend contract app.
2. Generate frontend services and DTOs from snapshot.
3. Type-check frontend.
4. Run contract audit against snapshot.

## Hard Rules
- Do not generate SDK/DTO from hand-written inventory files.
- Do not hardcode API path strings in runtime service modules.
- Do not add new API routers without registering and mounting them in the contract app.

## CI Gates
- OpenAPI reachability check must pass.
- Contract audit must report:
  - `missing == 0`
  - `method_mismatch == 0`
  - `unknown_calls == 0`
