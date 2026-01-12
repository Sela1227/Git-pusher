#!/usr/bin/env python3
"""
Git Pusher - 快速 Git 推送工具
功能：Push Develop / Release / 回復到穩定版
適用：Flet 0.70+
"""

import flet as ft
import subprocess
import json
import os
import random
import asyncio

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 顏色定義
COLOR_SELECTED = ft.Colors.ORANGE
COLOR_NORMAL = None


def load_config():
    """載入設定檔"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projects": [{} for _ in range(10)], "current_index": None}


def save_config(config):
    """儲存設定檔"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def run_git_command(cmd: str, cwd: str) -> tuple[bool, str]:
    """執行 git 指令，回傳 (成功與否, 訊息)"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except Exception as e:
        return False, str(e)


def main(page: ft.Page):
    page.title = "Git Pusher"
    page.window.width = 650
    page.window.height = 550
    page.padding = 20

    # 載入設定
    config = load_config()
    current_project = {"index": config.get("current_index"), "path": None, "name": None}

    # 如果有上次選擇的專案，載入它
    if current_project["index"] is not None:
        proj = config["projects"][current_project["index"]]
        if proj:
            current_project["path"] = proj.get("path")
            current_project["name"] = proj.get("name")

    # UI 元件
    status_text = ft.Text("", size=14)
    current_project_text = ft.Text("目前：未選擇專案", size=14, weight=ft.FontWeight.BOLD)
    commit_input = ft.TextField(
        label="Commit 訊息",
        hint_text="輸入 commit 訊息",
        expand=True,
    )

    # 專案按鈕列表
    project_buttons = []

    def update_current_display():
        """更新目前專案顯示"""
        if current_project["name"] and current_project["path"]:
            current_project_text.value = f"目前：{current_project['name']}（{current_project['path']}）"
        else:
            current_project_text.value = "目前：未選擇專案"

    def update_project_buttons():
        """更新專案按鈕文字和選中狀態"""
        for i, btn in enumerate(project_buttons):
            proj = config["projects"][i]
            label = proj.get("name", "空") if proj else "空"
            # 更新按鈕內的 Text
            btn.content.value = label
            # 更新選中狀態顏色
            if current_project["index"] == i:
                btn.style = ft.ButtonStyle(bgcolor=COLOR_SELECTED, color=ft.Colors.WHITE)
            else:
                btn.style = ft.ButtonStyle(bgcolor=COLOR_NORMAL)
        page.update()

    def set_status(success: bool, message: str):
        """設定狀態文字"""
        if success:
            status_text.value = f"✓ {message}"
            status_text.color = ft.Colors.GREEN
        else:
            status_text.value = f"✗ {message}"
            status_text.color = ft.Colors.RED

    def clear_status():
        """清除狀態文字"""
        status_text.value = "執行中..."
        status_text.color = ft.Colors.GREY
        page.update()

    def on_project_click(e):
        """點選專案按鈕"""
        index = int(e.control.data)
        proj = config["projects"][index]
        if proj and proj.get("path"):
            current_project["index"] = index
            current_project["path"] = proj["path"]
            current_project["name"] = proj["name"]
            config["current_index"] = index
            save_config(config)
            update_current_display()
            update_project_buttons()
            set_status(True, f"已切換到 {proj['name']}")
        else:
            set_status(False, "此按鈕尚未設定專案")

    # ========== FilePicker (service) ==========
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    async def on_save_project(e):
        """儲存專案 - async 版本"""
        clear_status()
        # 選擇資料夾
        result = await file_picker.get_directory_path(dialog_title="選擇專案資料夾")
        if not result:
            return

        selected_path = result

        # 顯示按鈕選擇對話框
        selected_slot = {"value": None}
        dialog_closed = {"value": False}

        def make_slot_handler(idx):
            def handler(e):
                selected_slot["value"] = idx
                dialog_closed["value"] = True
                page.pop_dialog()
            return handler

        def on_cancel_slot(e):
            dialog_closed["value"] = True
            page.pop_dialog()

        slot_buttons = []
        for i in range(10):
            proj = config["projects"][i]
            label = proj.get("name", "空") if proj else "空"
            slot_buttons.append(
                ft.Button(
                    content=ft.Text(f"{i + 1}: {label}"),
                    width=200,
                    on_click=make_slot_handler(i),
                )
            )

        slot_dialog = ft.AlertDialog(
            title=ft.Text("選擇儲存位置"),
            content=ft.Column(
                slot_buttons,
                spacing=5,
                scroll=ft.ScrollMode.AUTO,
                height=300,
            ),
            actions=[ft.Button(content=ft.Text("取消"), on_click=on_cancel_slot)],
        )
        page.show_dialog(slot_dialog)

        # 等待選擇
        while not dialog_closed["value"]:
            await asyncio.sleep(0.1)

        if selected_slot["value"] is None:
            return

        slot_index = selected_slot["value"]
        proj = config["projects"][slot_index]

        # 如果已有資料，詢問是否覆蓋
        if proj and proj.get("name"):
            confirm_result = {"value": None}
            confirm_closed = {"value": False}

            def on_confirm(e):
                confirm_result["value"] = True
                confirm_closed["value"] = True
                page.pop_dialog()

            def on_cancel(e):
                confirm_result["value"] = False
                confirm_closed["value"] = True
                page.pop_dialog()

            confirm_dialog = ft.AlertDialog(
                title=ft.Text("確認覆蓋"),
                content=ft.Text(f"按鈕 {slot_index + 1} 已有專案「{proj['name']}」，是否覆蓋？"),
                actions=[
                    ft.Button(content=ft.Text("取消"), on_click=on_cancel),
                    ft.Button(content=ft.Text("覆蓋"), on_click=on_confirm),
                ],
            )
            page.show_dialog(confirm_dialog)

            while not confirm_closed["value"]:
                await asyncio.sleep(0.1)

            if not confirm_result["value"]:
                return

        # 命名對話框
        name_input = ft.TextField(value=os.path.basename(selected_path), label="專案名稱", autofocus=True)
        name_result = {"value": None}
        name_closed = {"value": False}

        def on_name_confirm(e):
            name_result["value"] = name_input.value or os.path.basename(selected_path)
            name_closed["value"] = True
            page.pop_dialog()

        def on_name_cancel(e):
            name_closed["value"] = True
            page.pop_dialog()

        name_dialog = ft.AlertDialog(
            title=ft.Text("命名專案"),
            content=name_input,
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_name_cancel),
                ft.Button(content=ft.Text("確定"), on_click=on_name_confirm),
            ],
        )
        page.show_dialog(name_dialog)

        while not name_closed["value"]:
            await asyncio.sleep(0.1)

        if not name_result["value"]:
            return

        # 儲存
        config["projects"][slot_index] = {"name": name_result["value"], "path": selected_path}
        current_project["index"] = slot_index
        current_project["path"] = selected_path
        current_project["name"] = name_result["value"]
        config["current_index"] = slot_index
        save_config(config)
        update_project_buttons()
        update_current_display()
        set_status(True, f"已儲存到按鈕 {slot_index + 1}")

    async def on_rename_project(e):
        """重新命名目前專案"""
        clear_status()
        if current_project["index"] is None:
            set_status(False, "請先選擇專案")
            return

        current_name = current_project["name"] or ""

        # 命名對話框
        name_input = ft.TextField(value=current_name, label="新名稱", autofocus=True)
        name_result = {"value": None}
        name_closed = {"value": False}

        def on_name_confirm(e):
            name_result["value"] = name_input.value.strip()
            name_closed["value"] = True
            page.pop_dialog()

        def on_name_cancel(e):
            name_closed["value"] = True
            page.pop_dialog()

        name_dialog = ft.AlertDialog(
            title=ft.Text("重新命名專案"),
            content=name_input,
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_name_cancel),
                ft.Button(content=ft.Text("確定"), on_click=on_name_confirm),
            ],
        )
        page.show_dialog(name_dialog)

        while not name_closed["value"]:
            await asyncio.sleep(0.1)

        if not name_result["value"]:
            return

        # 更新名稱
        idx = current_project["index"]
        config["projects"][idx]["name"] = name_result["value"]
        current_project["name"] = name_result["value"]
        save_config(config)
        update_project_buttons()
        update_current_display()
        set_status(True, f"已重新命名為「{name_result['value']}」")

    def on_push_develop(e):
        """Push Develop"""
        clear_status()
        if not current_project["path"]:
            set_status(False, "請先選擇專案")
            return

        msg = commit_input.value.strip()
        if not msg:
            set_status(False, "請輸入 Commit 訊息")
            return

        cwd = current_project["path"]

        # git add .
        success, output = run_git_command("git add .", cwd)
        if not success:
            set_status(False, f"git add 失敗：{output}")
            return

        # git commit
        success, output = run_git_command(f'git commit -m "{msg}"', cwd)
        if not success:
            if "nothing to commit" in output:
                set_status(False, "沒有變更可提交")
            else:
                set_status(False, f"git commit 失敗：{output}")
            return

        # git push
        success, output = run_git_command("git push origin develop", cwd)
        if not success:
            set_status(False, f"git push 失敗：{output}")
            return

        set_status(True, "Push Develop 完成")
        commit_input.value = ""

    async def on_release(e):
        """Release - merge to main"""
        clear_status()
        if not current_project["path"]:
            set_status(False, "請先選擇專案")
            return

        develop_msg = commit_input.value.strip() or "Merge develop into main"

        # 建立輸入對話框
        release_input = ft.TextField(
            hint_text=develop_msg,
            hint_style=ft.TextStyle(color=ft.Colors.GREY_500),
            label="Main 分支訊息（不填則同上）",
            autofocus=True,
        )
        release_result = {"confirmed": False, "msg": None}
        release_closed = {"value": False}

        def on_confirm(e):
            release_result["confirmed"] = True
            release_result["msg"] = release_input.value.strip() or develop_msg
            release_closed["value"] = True
            page.pop_dialog()

        def on_cancel(e):
            release_closed["value"] = True
            page.pop_dialog()

        release_dialog = ft.AlertDialog(
            title=ft.Text("Release 到 Main"),
            content=release_input,
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_cancel),
                ft.Button(content=ft.Text("確定"), on_click=on_confirm),
            ],
        )
        page.show_dialog(release_dialog)

        while not release_closed["value"]:
            await asyncio.sleep(0.1)

        if not release_result["confirmed"]:
            return

        msg = release_result["msg"]
        cwd = current_project["path"]

        # git checkout main
        success, output = run_git_command("git checkout main", cwd)
        if not success:
            set_status(False, f"切換 main 失敗：{output}")
            return

        # git merge develop --no-ff
        success, output = run_git_command(f'git merge develop --no-ff -m "{msg}"', cwd)
        if not success:
            run_git_command("git checkout develop", cwd)
            set_status(False, f"Merge 失敗：{output}")
            return

        # git push origin main
        success, output = run_git_command("git push origin main", cwd)
        if not success:
            run_git_command("git checkout develop", cwd)
            set_status(False, f"Push main 失敗：{output}")
            return

        # git checkout develop
        run_git_command("git checkout develop", cwd)

        set_status(True, "Release 完成")
        commit_input.value = ""

    async def on_restore(e):
        """回復到穩定版"""
        clear_status()
        if not current_project["path"]:
            set_status(False, "請先選擇專案")
            return

        # 產生隨機四碼數字
        code = str(random.randint(1000, 9999))
        code_input = ft.TextField(label="請輸入上方數字確認", autofocus=True)
        restore_result = {"confirmed": False}
        restore_closed = {"value": False}

        def on_confirm(e):
            if code_input.value == code:
                restore_result["confirmed"] = True
            restore_closed["value"] = True
            page.pop_dialog()

        def on_cancel(e):
            restore_closed["value"] = True
            page.pop_dialog()

        restore_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ 危險操作"),
            content=ft.Column(
                [
                    ft.Text("這會覆蓋 develop 所有變更！", color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
                    ft.Text(f"請輸入 {code} 確認執行", size=16),
                    code_input,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_cancel),
                ft.Button(content=ft.Text("確定回復"), on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        page.show_dialog(restore_dialog)

        while not restore_closed["value"]:
            await asyncio.sleep(0.1)

        if not restore_result["confirmed"]:
            set_status(False, "驗證碼錯誤或取消")
            return

        cwd = current_project["path"]

        # git fetch origin (抓取遠端最新)
        success, output = run_git_command("git fetch origin", cwd)
        if not success:
            set_status(False, f"Fetch 失敗：{output}")
            return

        # 更新本地 main
        success, output = run_git_command("git checkout main", cwd)
        if not success:
            set_status(False, f"切換 main 失敗：{output}")
            return

        success, output = run_git_command("git reset --hard origin/main", cwd)
        if not success:
            set_status(False, f"Reset main 失敗：{output}")
            return

        # 更新本地 develop
        success, output = run_git_command("git checkout develop", cwd)
        if not success:
            set_status(False, f"切換 develop 失敗：{output}")
            return

        success, output = run_git_command("git reset --hard origin/main", cwd)
        if not success:
            set_status(False, f"Reset develop 失敗：{output}")
            return

        # git push --force develop
        success, output = run_git_command("git push origin develop --force", cwd)
        if not success:
            set_status(False, f"強制 Push 失敗：{output}")
            return

        set_status(True, "已回復到穩定版（main 和 develop 已同步）")

    async def on_init_git(e):
        """初始化 Git"""
        clear_status()
        if not current_project["path"]:
            set_status(False, "請先選擇專案")
            return

        cwd = current_project["path"]

        # 檢查是否已有 .git
        git_dir = os.path.join(cwd, ".git")
        if os.path.exists(git_dir):
            set_status(False, "此專案已有 .git，無需初始化")
            return

        # 輸入 remote URL
        url_input = ft.TextField(
            label="GitHub Repository URL",
            hint_text="https://github.com/username/repo.git",
            autofocus=True,
            width=400,
        )
        url_result = {"value": None}
        url_closed = {"value": False}

        def on_confirm(e):
            url_result["value"] = url_input.value.strip()
            url_closed["value"] = True
            page.pop_dialog()

        def on_cancel(e):
            url_closed["value"] = True
            page.pop_dialog()

        url_dialog = ft.AlertDialog(
            title=ft.Text("設定遠端 Repository"),
            content=url_input,
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_cancel),
                ft.Button(content=ft.Text("確定"), on_click=on_confirm),
            ],
        )
        page.show_dialog(url_dialog)

        while not url_closed["value"]:
            await asyncio.sleep(0.1)

        if not url_result["value"]:
            set_status(False, "已取消初始化")
            return

        remote_url = url_result["value"]

        # git init
        success, output = run_git_command("git init", cwd)
        if not success:
            set_status(False, f"git init 失敗：{output}")
            return

        # git add .
        success, output = run_git_command("git add .", cwd)
        if not success:
            set_status(False, f"git add 失敗：{output}")
            return

        # git commit
        success, output = run_git_command('git commit -m "Initial commit"', cwd)
        if not success:
            set_status(False, f"git commit 失敗：{output}")
            return

        # git branch -M main
        success, output = run_git_command("git branch -M main", cwd)
        if not success:
            set_status(False, f"建立 main 分支失敗：{output}")
            return

        # git remote add origin
        success, output = run_git_command(f"git remote add origin {remote_url}", cwd)
        if not success:
            set_status(False, f"設定 remote 失敗：{output}")
            return

        # git push -u origin main
        success, output = run_git_command("git push -u origin main", cwd)
        if not success:
            set_status(False, f"Push main 失敗：{output}")
            return

        # git checkout -b develop
        success, output = run_git_command("git checkout -b develop", cwd)
        if not success:
            set_status(False, f"建立 develop 分支失敗：{output}")
            return

        # git push -u origin develop
        success, output = run_git_command("git push -u origin develop", cwd)
        if not success:
            set_status(False, f"Push develop 失敗：{output}")
            return

        set_status(True, "Git 初始化完成（main + develop）")

    async def on_clear_project(e):
        """清除已儲存的專案"""
        clear_status()

        # 顯示按鈕選擇對話框
        selected_slot = {"value": None}
        dialog_closed = {"value": False}

        def make_slot_handler(idx):
            def handler(e):
                selected_slot["value"] = idx
                dialog_closed["value"] = True
                page.pop_dialog()
            return handler

        def on_cancel_slot(e):
            dialog_closed["value"] = True
            page.pop_dialog()

        slot_buttons = []
        for i in range(10):
            proj = config["projects"][i]
            label = proj.get("name", "空") if proj else "空"
            # 只有有設定的才能點
            is_empty = not proj or not proj.get("name")
            slot_buttons.append(
                ft.Button(
                    content=ft.Text(f"{i + 1}: {label}"),
                    width=200,
                    on_click=make_slot_handler(i),
                    disabled=is_empty,
                )
            )

        slot_dialog = ft.AlertDialog(
            title=ft.Text("選擇要清除的專案"),
            content=ft.Column(
                slot_buttons,
                spacing=5,
                scroll=ft.ScrollMode.AUTO,
                height=300,
            ),
            actions=[ft.Button(content=ft.Text("取消"), on_click=on_cancel_slot)],
        )
        page.show_dialog(slot_dialog)

        while not dialog_closed["value"]:
            await asyncio.sleep(0.1)

        if selected_slot["value"] is None:
            return

        slot_index = selected_slot["value"]
        proj = config["projects"][slot_index]
        proj_name = proj.get("name", "") if proj else ""

        # 確認對話框
        confirm_result = {"value": False}
        confirm_closed = {"value": False}

        def on_confirm(e):
            confirm_result["value"] = True
            confirm_closed["value"] = True
            page.pop_dialog()

        def on_cancel(e):
            confirm_closed["value"] = True
            page.pop_dialog()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("確認清除"),
            content=ft.Text(f"確定要清除「{proj_name}」嗎？"),
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=on_cancel),
                ft.Button(content=ft.Text("確定清除"), on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        page.show_dialog(confirm_dialog)

        while not confirm_closed["value"]:
            await asyncio.sleep(0.1)

        if not confirm_result["value"]:
            return

        # 清除專案
        config["projects"][slot_index] = {}

        # 如果清除的是目前選中的專案，清除 current_project
        if current_project["index"] == slot_index:
            current_project["index"] = None
            current_project["path"] = None
            current_project["name"] = None
            config["current_index"] = None

        save_config(config)
        update_project_buttons()
        update_current_display()
        set_status(True, f"已清除「{proj_name}」")

    # 建立專案按鈕
    for i in range(10):
        proj = config["projects"][i]
        label = proj.get("name", "空") if proj else "空"
        # 判斷是否為選中狀態
        is_selected = (current_project["index"] == i)
        btn = ft.Button(
            content=ft.Text(label),
            data=str(i),
            on_click=on_project_click,
            width=100,
            style=ft.ButtonStyle(
                bgcolor=COLOR_SELECTED if is_selected else COLOR_NORMAL,
                color=ft.Colors.WHITE if is_selected else None,
            ),
        )
        project_buttons.append(btn)

    # 初始化顯示
    update_current_display()

    # 版面配置
    page.add(
        # 專案按鈕區
        ft.Row(project_buttons[:5], spacing=5),
        ft.Row(project_buttons[5:], spacing=5),
        ft.Divider(),
        # 目前專案 + 管理
        current_project_text,
        ft.Row(
            [
                ft.Button(
                    content=ft.Text("儲存專案"),
                    on_click=lambda e: page.run_task(on_save_project, e),
                ),
                ft.Button(
                    content=ft.Text("重新命名"),
                    on_click=lambda e: page.run_task(on_rename_project, e),
                ),
                ft.Button(
                    content=ft.Text("初始化 Git"),
                    on_click=lambda e: page.run_task(on_init_git, e),
                ),
                ft.Button(
                    content=ft.Text("清除專案"),
                    on_click=lambda e: page.run_task(on_clear_project, e),
                ),
            ],
            spacing=10,
        ),
        ft.Divider(),
        # Commit 輸入
        commit_input,
        # 操作按鈕
        ft.Row(
            [
                ft.Button(
                    content=ft.Text("Push Develop"),
                    on_click=on_push_develop,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
                ),
                ft.Button(
                    content=ft.Text("Release"),
                    on_click=lambda e: page.run_task(on_release, e),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE),
                ),
                ft.Button(
                    content=ft.Text("回復到穩定版"),
                    on_click=lambda e: page.run_task(on_restore, e),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE),
                ),
            ],
            spacing=10,
        ),
        # 狀態顯示
        ft.Container(content=status_text, margin=ft.Margin.only(top=10)),
    )


if __name__ == "__main__":
    ft.run(main)
