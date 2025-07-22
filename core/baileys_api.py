import json
import time
import requests
from dataclasses import dataclass
from contextlib import closing
from typing import Any, Dict, List, Optional, Union, Iterator, TypedDict, NamedTuple

@dataclass
class SessionResult:
    created: bool
    qr: Optional[str] = None
    error: Optional[str] = None

class BaileysAPI:

    _qr_cache: dict[str, tuple[str, float]] = {}

    def __init__(
        self,
        base_url: str,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        :param base_url: URL base de tu API (p.ej. http://localhost:3000)
        :param session_id: sessionId por defecto (puedes pasar otro en cada llamada)
        :param api_key: valor de tu API‐Key para los endpoints protegidos
        :param timeout: tiempo de espera para las peticiones
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

    def set_session(self, session_id: str):
        """Fija un session_id por defecto para las siguientes llamadas."""
        self.session_id = session_id

    def set_api_key(self, api_key: str):
        """Fija o actualiza la API-Key para las siguientes llamadas."""
        self.api_key = api_key

    def _request(
        self,
        method: str,
        path: str,
        *,
        session_id: Optional[str] = None,
        params: Dict[str, Any] = None,
        json: Any = None,
        stream: bool = False,
        extra_headers: Dict[str, str] | None = None,
    ) -> Union[Dict[str, Any], List[Any], bytes, Iterator[bytes]]:
        # Resuelve sessionId en la ruta
        sid = session_id or self.session_id
        if '{sessionId}' in path:
            if not sid:
                raise ValueError("session_id no configurado para este endpoint")
            path = path.replace('{sessionId}', sid)

        url = f"{self.base_url}{path}"

        # Construye cabeceras
        headers: Dict[str, str] = {}
        if self.api_key:
            headers['x-api-key'] = self.api_key
        if extra_headers:
            headers.update(extra_headers)

        resp = self._session.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json,
            timeout=self.timeout,
            stream=stream
        )
        resp.raise_for_status()

        if stream:
            return resp.iter_content(chunk_size=8192)

        try:
            return resp.json()
        except ValueError:
            return resp.content

    # --- Sessions ---
    def list_sessions(self) -> List[Dict[str, Any]]:
        return self._request('GET', '/sessions')

    def find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/sessions/{session_id}")
    
    def session_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request('GET', '/sessions/{sessionId}/status', session_id=session_id)

    def add_session(self, session_id: str) -> Dict[str, Any]:
        """
        Low-level POST /sessions/add → body: { sessionId: <session_id> }
        Raises HTTPError on 4xx/5xx.
        """
        payload = { "sessionId": session_id }
        return self._request('POST', '/sessions/add', json=payload)
    
    def add_session_sse(self, session_id: str):
        """
        Abre la conexión SSE (`/add-sse`) y devuelve el generador de líneas.
        """
        extra_headers = {
            "Accept": "text/event-stream",   # cabecera obligatoria
        }

        # Llama usando *extra_headers*, no headers=
        stream = self._request(
            "GET",
            f"/sessions/{session_id}/add-sse",
            stream=True,
            extra_headers=extra_headers,
        )

        return map(lambda b: b.decode("utf-8"), stream)

    def delete_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request('DELETE', '/sessions/{sessionId}', session_id=session_id)

    # --- Chats ---
    def chat_list(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._request('GET', '/{sessionId}/chats', session_id=session_id)

    def load_conversation(self, jid: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request('GET', '/{sessionId}/chats/{jid}'.replace('{jid}', jid), session_id=session_id)

    def update_presence(self, jid: str, presence: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'POST',
            '/{sessionId}/chats/{jid}/presence'.replace('{jid}', jid),
            session_id=session_id,
            json=presence,
        )

    # --- Contacts ---
    def contact_list(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._request('GET', '/{sessionId}/contacts', session_id=session_id)

    def check_number(self, jid: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'GET',
            '/{sessionId}/contacts/{jid}'.replace('{jid}', jid),
            session_id=session_id,
        )

    def get_contact_photo(self, jid: str, session_id: Optional[str] = None) -> bytes:
        return self._request(
            'GET',
            '/{sessionId}/contacts/{jid}/photo'.replace('{jid}', jid),
            session_id=session_id,
            stream=False,
        )

    def blocklist(self, session_id: Optional[str] = None) -> List[str]:
        return self._request('GET', '/{sessionId}/contacts/blocklist', session_id=session_id)

    def update_blocklist(self, block_action: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        block_action: {"jid": "...", "action": "block"|"unblock"}
        """
        return self._request(
            'POST',
            '/{sessionId}/contacts/blocklist/update',
            session_id=session_id,
            json=block_action,
        )

    # --- Groups ---
    def group_list(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._request('GET', '/{sessionId}/groups', session_id=session_id)

    def group_metadata(self, jid: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'GET',
            '/{sessionId}/groups/{jid}'.replace('{jid}', jid),
            session_id=session_id,
        )

    def get_group_photo(self, jid: str, session_id: Optional[str] = None) -> bytes:
        return self._request(
            'GET',
            '/{sessionId}/groups/{jid}/photo'.replace('{jid}', jid),
            session_id=session_id,
            stream=False,
        )

    def create_group(self, group_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'POST',
            '/{sessionId}/groups/create',
            session_id=session_id,
            json=group_data,
        )

    def update_group_participants(self, jid: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'PUT',
            '/{sessionId}/groups/{jid}/update/participants'.replace('{jid}', jid),
            session_id=session_id,
            json=data,
        )

    def update_group_subject(self, jid: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'PUT',
            '/{sessionId}/groups/{jid}/update/subject'.replace('{jid}', jid),
            session_id=session_id,
            json=data,
        )

    def update_group_description(self, jid: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'PUT',
            '/{sessionId}/groups/{jid}/update/description'.replace('{jid}', jid),
            session_id=session_id,
            json=data,
        )

    def update_group_setting(self, jid: str, data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        data: {"setting": "..."} etc.
        """
        return self._request(
            'PUT',
            '/{sessionId}/groups/{jid}/update/setting'.replace('{jid}', jid),
            session_id=session_id,
            json=data,
        )

    def leave_group(self, jid: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'DELETE',
            '/{sessionId}/groups/{jid}'.replace('{jid}', jid),
            session_id=session_id,
        )

    def update_group_presence(self, jid: str, presence: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'POST',
            '/{sessionId}/groups/{jid}/presence'.replace('{jid}', jid),
            session_id=session_id,
            json=presence,
        )

    # --- Messages ---
    def message_list(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._request('GET', '/{sessionId}/messages', session_id=session_id)

    def send_message(self, msg: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'POST',
            '/{sessionId}/messages/send',
            session_id=session_id,
            json=msg,
        )

    def send_bulk_message(self, bulk: List[Dict[str, Any]], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'POST',
            '/{sessionId}/messages/send/bulk',
            session_id=session_id,
            json=bulk,
        )

    def download_media(self, media_req: Dict[str, Any], session_id: Optional[str] = None) -> bytes:
        # devuelve contenido binario
        return self._request(
            'POST',
            '/{sessionId}/messages/download',
            session_id=session_id,
            json=media_req,
        )

    def delete_message(self, delete_req: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'DELETE',
            '/{sessionId}/messages/delete',
            session_id=session_id,
            json=delete_req,
        )

    def delete_message_only_me(self, delete_req: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            'DELETE',
            '/{sessionId}/messages/delete/onlyme',
            session_id=session_id,
            json=delete_req,
        )
    

    # ****************************************************************************************************
    # Métodos para conexión de sesión única
    # ****************************************************************************************************
    def session_exists(self) -> bool:
        return self.find_session(self.session_id) is not None
        
    def _cache_qr(self, qr: str) -> None:
        self.__class__._qr_cache[self.session_id] = (qr, time.time())

    def _cached_qr(self) -> str | None:
        qr_tuple = self.__class__._qr_cache.get(self.session_id)
        if not qr_tuple:
            return None
        qr, ts = qr_tuple
        if time.time() - ts < 18:
            return qr
        self.__class__._qr_cache.pop(self.session_id, None)
        return None


    def get_qr_from_sse(self) -> str:
        """
        Devuelve un QR válido:
        1. Si hay uno fresco en caché → lo usa.
        2. Si no, abre /add-sse y espera el primer payload con `"qr"`.
           El stream se cierra automáticamente cuando el usuario
           escanee el código, pero nosotros salimos en cuanto
           recibimos el primer QR.
        """
        cached = self._cached_qr()
        if cached:
            return cached

        with closing(self.add_session_sse(self.session_id)) as stream:
            for chunk in stream:
                line = chunk.decode("utf-8", "ignore").strip()
                if line.startswith("data:"):
                    payload = json.loads(line[5:])
                    if "qr" in payload:
                        qr = payload["qr"]
                        self._cache_qr(qr)
                        return qr
        raise RuntimeError("No llegó ningún QR por SSE")
    

    def ensure_qr(self) -> Optional[str]:
        """
        Flujo completo para la vista:

        - Si la sesión aún no está `connected` → devuelve QR para
          mostrarlo en plantilla.
        - Si ya está conectada → devuelve None.
        """
        status = None
        try:
            status = self.session_status(self.session_id)["status"]
        except requests.HTTPError as e:
            # 404 → nunca se creó ⇒ tratamos como "no conectada"
            if e.response.status_code != 404:
                raise

        if status and status.lower() in ("connected", "authenticated"):
            return None  # ya no necesitamos QR

        # en cualquier otro caso (no existe / waiting / connecting) pedimos QR
        return self.get_qr_from_sse()