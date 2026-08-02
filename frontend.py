"""NiceGUI frontend for SnapShare.

Run ``python main.py`` then ``python frontend.py``. Set SNAPSHARE_API_URL when
its FastAPI service is not at http://127.0.0.1:8000.
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from nicegui import app, ui

API_URL = os.getenv('SNAPSHARE_API_URL', 'http://127.0.0.1:8000').rstrip('/')
STORAGE_SECRET = os.getenv('NICEGUI_STORAGE_SECRET', 'snapshare-local-development-secret')


class ApiError(Exception):
    pass


def _request(path: str, *, method: str = 'GET', token: str | None = None,
             data: bytes | None = None, content_type: str | None = None) -> Any:
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if content_type:
        headers['Content-Type'] = content_type
    request = urllib.request.Request(f'{API_URL}{path}', data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode('utf-8')
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')
        try:
            detail = json.loads(detail).get('detail', detail)
        except json.JSONDecodeError:
            pass
        raise ApiError(str(detail)) from error
    except urllib.error.URLError as error:
        raise ApiError(f'Cannot reach the API at {API_URL}. Is it running?') from error


async def api_request(*args: Any, **kwargs: Any) -> Any:
    return await asyncio.to_thread(_request, *args, **kwargs)


def multipart_body(filename: str, content: bytes, mime_type: str, caption: str) -> tuple[bytes, str]:
    boundary = '----SnapShareBoundary7MA4YWxkTrZu0gW'
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
         f'Content-Type: {mime_type}\r\n\r\n').encode(),
        content,
        f'\r\n--{boundary}--\r\n'.encode(),
    ]
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def human_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%b %d, %Y · %I:%M %p')
    except (TypeError, ValueError):
        return 'Just now'


@ui.page('/')
async def index() -> None:
    token = app.storage.user.get('token')
    email = app.storage.user.get('email', '')
    feed = ui.column().classes('w-full max-w-3xl mx-auto gap-5')
    upload_dialog = ui.dialog()

    async def load_feed() -> None:
        feed.clear()
        if not app.storage.user.get('token'):
            with feed:
                ui.label('Welcome to SnapShare').classes('text-3xl font-bold text-slate-900')
                ui.label("Sign in to see your community's latest photos and videos.").classes('text-slate-500')
            return
        try:
            posts = await api_request('/feed', token=app.storage.user['token'])
        except ApiError as error:
            with feed:
                ui.label('Couldn’t load the feed').classes('text-xl font-semibold text-slate-800')
                ui.label(str(error)).classes('text-red-500')
                ui.button('Try again', on_click=load_feed).props('outline color=primary')
            return
        with feed:
            if not posts:
                with ui.card().classes('w-full p-8 text-center rounded-2xl shadow-sm'):
                    ui.icon('photo_library', size='3rem').classes('text-violet-500')
                    ui.label('The feed is ready for its first memory.').classes('text-lg font-semibold mt-2')
                    ui.label('Share a photo or video to get things started.').classes('text-slate-500')
            for post in posts:
                with ui.card().classes('w-full overflow-hidden rounded-2xl shadow-sm p-0'):
                    with ui.row().classes('w-full items-center justify-between p-4'):
                        with ui.row().classes('items-center gap-3'):
                            ui.avatar(post.get('email', '?')[0].upper()).classes('bg-violet-100 text-violet-700 font-bold')
                            with ui.column().classes('gap-0'):
                                ui.label(post.get('email', 'Unknown')).classes('font-semibold text-slate-800')
                                ui.label(human_time(post.get('created_at', ''))).classes('text-xs text-slate-400')
                        if post.get('is_owner'):
                            async def delete_post(post_id: str = post['id']) -> None:
                                try:
                                    await api_request(f'/posts/{post_id}', method='DELETE', token=app.storage.user['token'])
                                    ui.notify('Post deleted', type='positive')
                                    await load_feed()
                                except ApiError as error:
                                    ui.notify(str(error), type='negative')
                            ui.button(icon='delete_outline', on_click=delete_post).props('flat round color=grey')
                    if post.get('file_type') == 'video':
                        ui.video(post['url']).classes('w-full max-h-[540px] bg-black')
                    else:
                        ui.image(post['url']).classes('w-full max-h-[540px] object-contain bg-slate-50')
                    if post.get('caption'):
                        ui.label(post['caption']).classes('p-4 text-slate-700 whitespace-pre-wrap')

    with upload_dialog, ui.card().classes('w-[min(92vw,34rem)] rounded-2xl p-6'):
        ui.label('Share a memory').classes('text-2xl font-bold')
        caption = ui.textarea('Caption').props('outlined autogrow maxlength=500').classes('w-full')
        selected_file: dict[str, Any] = {}
        status = ui.label().classes('text-sm text-slate-500')

        async def receive_upload(event: Any) -> None:
            selected_file['name'] = event.file.name
            selected_file['mime'] = event.file.content_type or 'application/octet-stream'
            selected_file['bytes'] = await event.file.read()
            status.set_text(f'Selected: {event.file.name}')

        ui.upload(on_upload=receive_upload, auto_upload=True, label='Choose photo or video').props(
            'accept=.jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.webm max-files=1').classes('w-full')

        async def submit_post() -> None:
            if not selected_file:
                ui.notify('Choose a photo or video first', type='warning')
                return
            body, content_type = multipart_body(selected_file['name'], selected_file['bytes'], selected_file['mime'], caption.value or '')
            try:
                await api_request('/upload', method='POST', token=app.storage.user['token'], data=body, content_type=content_type)
                upload_dialog.close()
                ui.notify('Shared to your feed', type='positive')
                await load_feed()
            except ApiError as error:
                ui.notify(str(error), type='negative')

        with ui.row().classes('w-full justify-end gap-2 mt-3'):
            ui.button('Cancel', on_click=upload_dialog.close).props('flat')
            ui.button('Share', icon='send', on_click=submit_post).props('color=primary')

    auth_dialog = ui.dialog()
    with auth_dialog, ui.card().classes('w-[min(92vw,28rem)] rounded-2xl p-6'):
        ui.label('Welcome to SnapShare').classes('text-2xl font-bold')
        ui.label('Save and share the moments worth keeping.').classes('text-slate-500')
        auth_email = ui.input('Email').props('outlined type=email').classes('w-full mt-3')
        password = ui.input('Password').props('outlined type=password').classes('w-full')

        async def login() -> None:
            encoded = urllib.parse.urlencode({'username': auth_email.value or '', 'password': password.value or ''}).encode()
            try:
                result = await api_request('/auth/jwt/login', method='POST', data=encoded, content_type='application/x-www-form-urlencoded')
                app.storage.user['token'] = result['access_token']
                app.storage.user['email'] = auth_email.value
                auth_dialog.close()
                ui.navigate.to('/')
            except ApiError as error:
                ui.notify(str(error), type='negative')

        async def register() -> None:
            payload = json.dumps({'email': auth_email.value or '', 'password': password.value or ''}).encode()
            try:
                await api_request('/auth/register', method='POST', data=payload, content_type='application/json')
                ui.notify('Account created — you can sign in now.', type='positive')
            except ApiError as error:
                ui.notify(str(error), type='negative')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Create account', on_click=register).props('flat color=primary')
            ui.button('Sign in', on_click=login).props('color=primary')

    with ui.header().classes('bg-white text-slate-800 border-b border-slate-100 shadow-none'):
        with ui.row().classes('w-full max-w-6xl mx-auto items-center justify-between px-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('camera_alt', size='1.7rem').classes('text-violet-600')
                ui.label('SnapShare').classes('text-xl font-bold tracking-tight')
            with ui.row().classes('items-center gap-2'):
                if token:
                    ui.label(email).classes('hidden sm:block text-sm text-slate-500')
                    ui.button('Share', icon='add_a_photo', on_click=upload_dialog.open).props('color=primary unelevated')
                    def logout() -> None:
                        app.storage.user.clear()
                        ui.navigate.to('/')
                    ui.button(icon='logout', on_click=logout).props('flat round color=grey')
                else:
                    ui.button('Sign in', icon='login', on_click=auth_dialog.open).props('color=primary unelevated')

    ui.add_head_html('<style>body { background: #f8fafc; } .nicegui-content { padding: 2rem 1rem 4rem; }</style>')
    await load_feed()


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='SnapShare', port=int(os.getenv('PORT', '8080')), storage_secret=STORAGE_SECRET)