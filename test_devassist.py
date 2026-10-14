"""Тесты Дня 31 — ассистент разработчика (specs/031-dev-assistant).

Запуск — в составе безопасного набора: `.venv/bin/python -B run_tests.py`.
Настоящий проект (CRM) в тестах не участвует: репозитории git — временные.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from agent.service import pd


class ТочныйПрофильПД(unittest.TestCase):
    """plan D-02a: маска для документации проекта не портит техническую латиницу."""

    def setUp(self) -> None:
        self.каталог = tempfile.TemporaryDirectory()
        путь = os.path.join(self.каталог.name, "pd-names.txt")
        with open(путь, "w", encoding="utf-8") as f:
            f.write("# тестовый список\nЗаглушкин\n")
        self.окружение = mock.patch.dict(os.environ, {"PD_NAMES": путь})
        self.окружение.start()

    def tearDown(self) -> None:
        self.окружение.stop()
        self.каталог.cleanup()

    def test_техническая_латиница_не_трогается(self) -> None:
        for текст in ("Только ORM-выражения поддерева", "из «позже» в MVP владельца",
                      "адрес IP общества", "`BODY.PEEK[]` и POST запрос", "по JSON, а не по HTML",
                      "sha256:04878004256f6dae989736e437b6fb074cb4e6c3"):
            with self.subTest(текст=текст):
                итог, виды = pd.скрыть(текст, профиль="точный")
                self.assertEqual(итог, текст)
                self.assertEqual(виды, {})

    def test_полный_профиль_по_умолчанию_прежний(self) -> None:
        # Полный профиль ловит латинских двойников — потому и портит «MVP владельца».
        итог, _ = pd.скрыть("M.B Заглушкин подписал")
        self.assertNotIn("Заглушкин", итог)
        self.assertEqual(pd.скрыть("M.B Заглушкин подписал"), pd.скрыть("M.B Заглушкин подписал", профиль="полный"))

    def test_точный_ловит_настоящие_пд(self) -> None:
        случаи = {
            "список «Иван Заглушкин», и всё": "фамилия из списка",
            "автор ЗАГЛУШКИН ответил": "фамилия из списка",
            "подписал А.В. Петров вчера": "инициалы и фамилия",
            "подписал Петров А.В. вчера": "фамилия и инициалы",
            "пишите на admin@corp.example.ru": "e-mail",
            "звоните +7 (473) 123-45-67": "телефон",
            "Ирина Сергеевна сказала": "отчество",
        }
        for текст, вид in случаи.items():
            with self.subTest(текст=текст):
                итог, виды = pd.скрыть(текст, профиль="точный")
                self.assertIn(pd.МАСКА, итог)
                self.assertIn(вид, виды)

    def test_точный_не_поднимает_ошибку_на_неоднозначном(self) -> None:
        with self.assertRaises(pd.ОшибкаМаскирования):
            pd.скрыть("Подписал Анна Сергеевна Неизвестнова")
        итог, виды = pd.скрыть("Подписал Анна Сергеевна Неизвестнова", профиль="точный")
        self.assertIn(pd.МАСКА, итог)
        self.assertNotIn("Сергеевна", итог)

    def test_фамилия_перед_инициалами_и_строчное_слово(self) -> None:
        # «Петров А.В. вчера» читалось как «А.В. вчера»: маска съедала инициалы, фамилия
        # оставалась открытой — и в полном профиле (/doc Дня 30), и в точном.
        for профиль in pd.ПРОФИЛИ:
            for текст in ("подписал Петров А.В. вчера", "подписал А.В. Петров вчера"):
                with self.subTest(профиль=профиль, текст=текст):
                    итог, _ = pd.скрыть(текст, профиль=профиль)
                    self.assertNotIn("Петров", итог)
                    self.assertIn("вчера", итог)

    def test_неизвестный_профиль(self) -> None:
        with self.assertRaises(ValueError):
            pd.скрыть("текст", профиль="мягкий")


def временный_репозиторий(каталог: str, файлы: dict[str, str]) -> str:
    """git init + коммит файлов во временном каталоге; вернуть путь."""
    import subprocess
    for путь, текст in файлы.items():
        полный = os.path.join(каталог, путь)
        os.makedirs(os.path.dirname(полный), exist_ok=True)
        with open(полный, "w", encoding="utf-8") as f:
            f.write(текст)
    окр = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    for команда in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "начало"]):
        subprocess.run(["git", "-C", каталог, *команда], check=True, env=окр, capture_output=True)
    return каталог


class ПроектыИИндекс(unittest.TestCase):
    """spec FR-01–FR-03, plan D-01, D-02."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        корень = self.tmp.name
        names = os.path.join(корень, "pd-names.txt")
        with open(names, "w", encoding="utf-8") as f:
            f.write("Заглушкин\n")
        self.окружение = mock.patch.dict(os.environ, {"PD_NAMES": names})
        self.окружение.start()
        self.репо = временный_репозиторий(os.path.join(корень, "proj"), {
            "README.md": "# Проект\n\nСтек — Django. Автор Иван Заглушкин. Только ORM-выражения.\n",
            "docs/guide.md": "# Гид\n\n## Раздел\n\nТекст раздела про MVP.\n",
            "docs/reviews/r1.md": "# Ревью\n\nне индексировать\n",
            "specs/001-a/spec.md": "# Спека\n\nтребования\n",
            "backend/apps/x/models.py": "class Заявка:\n    поле = 1\n",
            "backend/apps/x/views.py": "def вид():\n    pass\n",
            "HANDOFF.md": "рабочий журнал\n",
        })
        with open(os.path.join(self.репо, "docs", "untracked.md"), "w", encoding="utf-8") as f:
            f.write("не под git\n")
        self.конфиг = os.path.join(корень, "projects.json")
        import json
        with open(self.конфиг, "w", encoding="utf-8") as f:
            json.dump({"по_умолчанию": "t", "проекты": {"t": {
                "путь": self.репо, "описание": "тест", "индекс": "idx/t",
                "включить": ["README.md", "docs/*.md", "docs/**/*.md", "specs/**/*.md", "backend/**/models.py"],
                "исключить": ["docs/reviews/**", "HANDOFF.md"]}}}, f, ensure_ascii=False)

    def tearDown(self) -> None:
        self.окружение.stop()
        self.tmp.cleanup()

    def test_загрузка_и_ошибки(self) -> None:
        from agent.devassist import project
        п = project.загрузить(путь=self.конфиг)
        self.assertEqual(п.имя, "t")
        self.assertEqual(п.индекс, os.path.join(self.tmp.name, "idx", "t"))
        with self.assertRaises(project.ОшибкаПроекта):
            project.загрузить("нет-такого", путь=self.конфиг)
        with mock.patch.dict(os.environ, {"PROJECT_T_DIR": "/нет/такого/каталога"}):
            with self.assertRaises(project.ОшибкаПроекта):
                project.файлы(project.загрузить(путь=self.конфиг))

    def test_только_файлы_под_git_по_спискам(self) -> None:
        from agent.devassist import project
        п = project.загрузить(путь=self.конфиг)
        self.assertEqual(project.файлы(п), ["README.md", "backend/apps/x/models.py", "docs/guide.md",
                                            "specs/001-a/spec.md"])

    def test_маска_до_индекса_и_повторная_подготовка(self) -> None:
        from agent.devassist import project
        п = project.загрузить(путь=self.конфиг)
        отчёт = project.подготовить(п)
        self.assertEqual(len(отчёт["изменено"]), 4)
        self.assertEqual(отчёт["замены_пд"], {"фамилия из списка": 1})
        with open(os.path.join(п.src, "README.md"), encoding="utf-8") as f:
            текст = f.read()
        self.assertNotIn("Заглушкин", текст)
        self.assertIn("ORM-выражения", текст)          # точный профиль, не полный
        повтор = project.подготовить(п)
        self.assertEqual((повтор["изменено"], повтор["удалено"]), ([], []))
        with open(os.path.join(self.репо, "docs", "guide.md"), "a", encoding="utf-8") as f:
            f.write("\nещё строка\n")
        os.remove(os.path.join(self.репо, "specs", "001-a", "spec.md"))
        import subprocess
        subprocess.run(["git", "-C", self.репо, "rm", "-q", "--cached", "specs/001-a/spec.md"], check=True)
        третий = project.подготовить(п)
        self.assertEqual(третий["изменено"], ["docs/guide.md"])
        self.assertEqual(третий["удалено"], ["specs/001-a/spec.md"])
        self.assertFalse(os.path.exists(os.path.join(п.src, "specs", "001-a", "spec.md")))

    def test_индекс_источник_путь_в_проекте(self) -> None:
        from agent.devassist import project
        п = project.загрузить(путь=self.конфиг)
        отчёт = project.построить(п, эмбеддер="хэш")
        self.assertGreater(отчёт["фрагментов"], 0)
        self.assertTrue(project.индекс_есть(п))
        найдено = project.индексатор(п, "хэш").найти("Заявка поле", "структура", 10)
        источники = {ф.чанк.паспорт()["source"] for ф in найдено}
        self.assertEqual(источники, {"README.md", "backend/apps/x/models.py", "docs/guide.md",
                                     "specs/001-a/spec.md"})
        второй = project.построить(п, эмбеддер="хэш")
        self.assertEqual(второй["из_кэша"], второй["фрагментов"])

    def test_git_только_без_блокировок(self) -> None:
        from agent.devassist import project
        окр = project.окружение_git()
        self.assertEqual((окр["GIT_OPTIONAL_LOCKS"], окр["GIT_TERMINAL_PROMPT"]), ("0", "0"))


class GitСервер(unittest.TestCase):
    """spec FR-04, plan D-03: git_server.py — только чтение, белый список, пределы."""

    @classmethod
    def setUpClass(cls) -> None:
        import subprocess
        cls.tmp = tempfile.TemporaryDirectory()
        cls.репо = временный_репозиторий(os.path.join(cls.tmp.name, "r"), {
            "README.md": "# Проект\n", "specs/001/spec.md": "# Спека\n", "docs/a.md": "# А\n"})
        окр = dict(os.environ, GIT_AUTHOR_NAME="Автор Секретов", GIT_AUTHOR_EMAIL="a@b",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull)
        with open(os.path.join(cls.репо, "docs", "a.md"), "a", encoding="utf-8") as f:
            f.write("вторая строка\n")
        subprocess.run(["git", "-C", cls.репо, "commit", "-qam", "вторая правка"], check=True, env=окр)
        # Ловушки локального конфига: внешний diff, textconv и fsmonitor — программы, которые
        # git исполнил бы при чтении. Сервер не должен их запускать.
        cls.метка = os.path.join(cls.tmp.name, "запущено")
        скрипт = os.path.join(cls.tmp.name, "ловушка.sh")
        with open(скрипт, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\necho $0 >> '{cls.метка}'\n")
        os.chmod(скрипт, 0o755)
        for ключ, значение in (("diff.external", скрипт), ("core.fsmonitor", скрипт),
                               ("diff.ловушка.textconv", скрипт)):
            subprocess.run(["git", "-C", cls.репо, "config", ключ, значение], check=True)
        with open(os.path.join(cls.репо, ".gitattributes"), "w", encoding="utf-8") as f:
            f.write("*.md diff=ловушка\n")
        with open(os.path.join(cls.репо, "README.md"), "a", encoding="utf-8") as f:
            f.write("незакоммиченное\n")
        cls.окружение = mock.patch.dict(os.environ, {"GIT_ROOT": cls.репо})
        cls.окружение.start()
        import git_server
        cls.м = git_server

    @classmethod
    def tearDownClass(cls) -> None:
        cls.окружение.stop()
        cls.tmp.cleanup()

    def вызвать(self, имя: str, аргументы: dict | None = None):
        import anyio
        from mcp import Client

        async def вызов():
            async with Client(self.м.сервер) as клиент:
                return await клиент.call_tool(имя, аргументы or {})

        return anyio.run(вызов)

    def test_инструменты_только_чтение(self) -> None:
        import anyio
        from mcp import Client

        async def список():
            async with Client(self.м.сервер) as клиент:
                return (await клиент.list_tools()).tools

        инструменты = anyio.run(список)
        self.assertEqual({и.name for и in инструменты},
                         {"git_branch", "git_status", "git_ls_files", "git_diff", "git_log"})
        for и in инструменты:
            with self.subTest(и.name):
                self.assertTrue(и.annotations.read_only_hint)
                self.assertFalse(и.annotations.destructive_hint)
                self.assertFalse(и.annotations.open_world_hint)

    def test_ветка_статус_файлы(self) -> None:
        в = self.м.ветка()
        self.assertEqual(в["ветка"], "main")
        self.assertFalse(в["отделённый"])
        с = self.м.статус()
        self.assertFalse(с["чисто"])
        self.assertTrue(any("README.md" in ф for ф in с["файлы"]))
        self.assertEqual(self.м.файлы("specs/**")["файлы"], ["specs/001/spec.md"])
        self.assertEqual(self.м.файлы("*.md")["файлы"], ["README.md"])   # * — внутри каталога
        self.assertEqual(self.м.файлы("", предел=1)["обрезано"], True)

    def test_diff_и_журнал(self) -> None:
        рабочий = self.м.разница()
        self.assertIn("незакоммиченное", рабочий["diff"])
        между = self.м.разница("HEAD~1", "HEAD")
        self.assertIn("вторая строка", между["diff"])
        self.assertIn("docs/a.md", между["сводка"])
        ж = self.м.журнал(5)
        self.assertEqual([к["тема"] for к in ж["коммиты"]], ["вторая правка", "начало"])
        self.assertNotIn("Автор", str(ж))                                 # авторов нет
        with mock.patch.object(self.м, "ПРЕДЕЛ_DIFF", 10):
            self.assertTrue(self.м.разница()["обрезано"])

    def test_ловушки_конфига_не_исполняются(self) -> None:
        self.м.статус(); self.м.разница(); self.м.разница("HEAD~1", "HEAD"); self.м.журнал()
        self.assertFalse(os.path.exists(self.метка), "git исполнил программу из локального конфига")

    def test_отказы_понятны(self) -> None:
        for имя, аргументы, слово in (
                ("git_diff", {"from_ref": "--output=/tmp/x"}, "не ссылка"),
                ("git_diff", {"from_ref": "нет-такой-ветки"}, "не ссылка"),
                ("git_diff", {"from_ref": "no-such-branch"}, "нет"),
                ("git_ls_files", {"pattern": "../etc"}, "вне проекта"),
                ("git_ls_files", {"pattern": "/etc/passwd"}, "вне проекта"),
                ("git_log", {"path": ":(top)x"}, "вне проекта")):
            with self.subTest(аргументы=аргументы):
                итог = self.вызвать(имя, аргументы)
                self.assertTrue(итог.is_error)
                self.assertIn(слово, итог.content[0].text)
        with self.assertRaises(self.м.ОшибкаЗапроса):
            self.м._git("commit", "-m", "x")
        with self.assertRaises(self.м.ОшибкаЗапроса):
            self.м._git("push")

    def test_без_блокировок_и_пароля(self) -> None:
        окр = self.м.окружение()
        self.assertEqual((окр["GIT_OPTIONAL_LOCKS"], окр["GIT_TERMINAL_PROMPT"]), ("0", "0"))
        индекс = os.path.join(self.репо, ".git", "index")
        до = os.stat(индекс).st_mtime_ns
        for _ in range(3):
            self.м.статус(); self.м.ветка(); self.м.разница()
        self.assertEqual(os.stat(индекс).st_mtime_ns, до)

    def test_корень_не_задан(self) -> None:
        with mock.patch.dict(os.environ, {"GIT_ROOT": ""}):
            with self.assertRaises(self.м.ОшибкаЗапроса):
                self.м.ветка()


if __name__ == "__main__":
    unittest.main()
