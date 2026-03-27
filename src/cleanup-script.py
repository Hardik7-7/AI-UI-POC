import argparse
import time
from typing import Iterable, List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse

import requests


DONE_STATUSES = {4, 5, 6, 8}  # Finished, Failed, Cancel, Cancelled


def normalize_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base-url must include scheme and host, e.g. https://host")
    if parsed.port is None:
        netloc = f"{parsed.hostname}:8086"
        if parsed.username or parsed.password:
            auth = ""
            if parsed.username:
                auth += parsed.username
                if parsed.password:
                    auth += f":{parsed.password}"
            netloc = f"{auth}@{netloc}"
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed).rstrip('/')


def build_url(base_url: str, path: str) -> str:
    return base_url.rstrip('/') + path


def auth_token(session: requests.Session, base_url: str, username: str, password: str, key_name: Optional[str]) -> str:
    url = build_url(base_url, '/auth/')
    payload = {
        'username': username,
        'password': password,
    }
    if key_name:
        payload['key_name'] = key_name

    resp = session.post(url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f'Auth failed: {resp.status_code} {resp.text}')
    data = resp.json()
    token = data.get('token')
    if not token:
        raise RuntimeError(f'Auth response missing token: {data}')
    return token


def fetch_all(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    page = 1
    while True:
        page_params = dict(params)
        page_params['page'] = page
        resp = session.get(url, params=page_params, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f'List failed: {resp.status_code} {resp.text}')
        data = resp.json()
        page_results = data.get('results', [])
        results.extend(page_results)
        next_page = data.get('next')
        if not next_page:
            break
        page = next_page
    return results


def filter_prefix(items: Iterable[Dict[str, Any]], prefix: str) -> List[Dict[str, Any]]:
    pref = prefix.lower()
    out = []
    for it in items:
        name = (it.get('name') or '').lower()
        if name.startswith(pref):
            out.append(it)
    return out


def chunked(seq: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def deploy_bulk_delete(session: requests.Session, base_url: str, uuids: List[str], force: bool, lib_delete: bool, chunk_size: int) -> List[str]:
    if not uuids:
        return []
    url = build_url(base_url, '/deploy/rest/bulkops/')
    all_job_uuids: List[str] = []
    for chunk in chunked(uuids, chunk_size):
        payload = {
            'machine_list': chunk,
            'op': 'delete',
            'force': force,
            'lib_delete': lib_delete,
        }
        resp = session.post(url, json=payload, timeout=300)
        if resp.status_code not in (201, 207):
            raise RuntimeError(f'Deploy bulk delete failed: {resp.status_code} {resp.text}')
        data = resp.json()
        for item in data.get('success', []):
            job_list = item.get('job_uuid', [])
            if isinstance(job_list, list):
                all_job_uuids.extend(job_list)
    return all_job_uuids


def poll_tasks(session: requests.Session, base_url: str, task_uuids: List[str], poll_interval: int, timeout_sec: int) -> None:
    if not task_uuids:
        return
    url_tpl = build_url(base_url, '/rtask/rest/detail/{uuid}/')
    pending = set(task_uuids)
    start = time.time()
    while pending:
        if time.time() - start > timeout_sec:
            raise TimeoutError(f'Timeout waiting for tasks: {sorted(pending)}')
        done_now = []
        for t_uuid in list(pending):
            resp = session.get(url_tpl.format(uuid=t_uuid), timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f'Rtask detail failed: {resp.status_code} {resp.text}')
            data = resp.json()
            status = data.get('status')
            if status in DONE_STATUSES:
                done_now.append(t_uuid)
        for t_uuid in done_now:
            pending.discard(t_uuid)
        if pending:
            time.sleep(poll_interval)


def machine_bulk_delete(session: requests.Session, base_url: str, uuids: List[str], chunk_size: int) -> None:
    if not uuids:
        return
    url = build_url(base_url, '/library/rest/bulkdelete/')
    for chunk in chunked(uuids, chunk_size):
        payload = {'machine_list': chunk}
        resp = session.delete(url, json=payload, timeout=300)
        if resp.status_code == 204:
            continue
        if resp.status_code == 207:
            data = resp.json()
            failures = data.get('failure', [])
            if failures:
                raise RuntimeError(f'Library bulk delete partial failure: {failures}')
            continue
        raise RuntimeError(f'Library bulk delete failed: {resp.status_code} {resp.text}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Bulk delete deploys and libraries by name prefix, with rtask polling.')
    parser.add_argument('--base-url', required=True, help='Base URL, e.g. https://host')
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--key-name', default=None)
    parser.add_argument('--prefix', default='test_ui', help='Name prefix to target')
    parser.add_argument('--search', default=None, help='Search param (defaults to prefix)')
    parser.add_argument('--scope', default='all', choices=['all', 'my'])
    parser.add_argument('--page-size', type=int, default=500)
    parser.add_argument('--chunk-size', type=int, default=200)
    parser.add_argument('--force-delete', action='store_true')
    parser.add_argument('--lib-delete', action='store_true', help='Also delete source library when deleting deploys')
    parser.add_argument('--poll-interval', type=int, default=10)
    parser.add_argument('--timeout-sec', type=int, default=3600)
    parser.add_argument('--insecure', action='store_true', help='Disable TLS verification')
    args = parser.parse_args()

    search_val = args.search or args.prefix

    base_url = normalize_base_url(args.base_url)
    session = requests.Session()
    session.verify = not args.insecure
    session.headers.update({'Accept': 'application/json'})

    token = auth_token(session, base_url, args.username, args.password, args.key_name)
    session.headers.update({'Authorization': f'Token {token}'})

    # 1) Deploy listing
    deploy_list_url = build_url(base_url, '/deploy/rest/deploylist/')
    deploy_items = fetch_all(session, deploy_list_url, {
        'search': search_val,
        'scope': args.scope,
        'page_size': args.page_size,
    })
    deploy_items = filter_prefix(deploy_items, args.prefix)
    deploy_uuids = [it['uuid'] for it in deploy_items if it.get('uuid')]

    print(f'Found {len(deploy_uuids)} deployed machines with prefix "{args.prefix}"')

    # 2) Bulk delete deploys
    deploy_task_uuids = deploy_bulk_delete(
        session, base_url, deploy_uuids,
        force=args.force_delete, lib_delete=args.lib_delete,
        chunk_size=args.chunk_size
    )

    # 3) Poll tasks (deploy deletions)
    print(f'Polling {len(deploy_task_uuids)} deploy delete task(s)')
    poll_tasks(session, base_url, deploy_task_uuids, args.poll_interval, args.timeout_sec)
    print('Deploy delete tasks completed')

    # 4) Machine listing
    machine_list_url = build_url(base_url, '/library/rest/viewmachinelist/')
    machine_items = fetch_all(session, machine_list_url, {
        'search': search_val,
        'scope': args.scope,
        'page_size': args.page_size,
    })
    machine_items = filter_prefix(machine_items, args.prefix)
    machine_uuids = [it['uuid'] for it in machine_items if it.get('uuid')]

    print(f'Found {len(machine_uuids)} library machines with prefix "{args.prefix}"')

    # 5) Bulk delete libraries (synchronous)
    machine_bulk_delete(session, base_url, machine_uuids, args.chunk_size)
    print('Library bulk delete completed (synchronous)')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
