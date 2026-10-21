from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts" / "results"
OUT_REPO = ROOT / "report" / "Lab3_MapReduce_DevOps.pdf"
OUT_USER = ROOT / "outputs" / "Lab3_MapReduce_DevOps.pdf"
TMP = ROOT / "tmp" / "pdfs"
REPOSITORY_URL = "https://github.com/DariaSide/lab3"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


analysis = load("analysis.json")
profile = load("profiling.json")
verify = load("verification.json")
prepare = json.loads((ROOT / "data" / "prepare_metadata.json").read_text(encoding="utf-8"))

font_dir = ROOT / ".venv/lib/python3.9/site-packages/matplotlib/mpl-data/fonts/ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(font_dir / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuMono", str(font_dir / "DejaVuSansMono.ttf")))

BLUE = colors.HexColor("#173B57")
TEAL = colors.HexColor("#168A8A")
LIGHT = colors.HexColor("#EAF2F6")
INK = colors.HexColor("#1D2730")
MUTED = colors.HexColor("#5C6973")
GREEN = colors.HexColor("#257A4B")
RED = colors.HexColor("#A33A3A")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleRU", parent=styles["Title"], fontName="DejaVu-Bold", fontSize=25, leading=31, textColor=BLUE, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle(name="Sub", fontName="DejaVu", fontSize=11, leading=16, textColor=MUTED, spaceAfter=8))
styles.add(ParagraphStyle(name="H1RU", parent=styles["Heading1"], fontName="DejaVu-Bold", fontSize=17, leading=22, textColor=BLUE, spaceBefore=8, spaceAfter=10))
styles.add(ParagraphStyle(name="H2RU", parent=styles["Heading2"], fontName="DejaVu-Bold", fontSize=12, leading=16, textColor=TEAL, spaceBefore=7, spaceAfter=6))
styles.add(ParagraphStyle(name="BodyRU", parent=styles["BodyText"], fontName="DejaVu", fontSize=9.2, leading=13.5, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallRU", fontName="DejaVu", fontSize=7.5, leading=10.5, textColor=INK))
styles.add(ParagraphStyle(name="MonoRU", fontName="DejaVuMono", fontSize=7.2, leading=10.1, textColor=colors.HexColor("#E8EEF2"), backColor=colors.HexColor("#14232E"), borderPadding=8, spaceAfter=8))
styles.add(ParagraphStyle(name="Callout", fontName="DejaVu-Bold", fontSize=10, leading=14, textColor=BLUE, backColor=LIGHT, borderPadding=9, spaceAfter=10))


def p(text, style="BodyRU"):
    return Paragraph(text, styles[style])


def fmt_money(value):
    return "-" if value is None else f"{value:,.0f}".replace(",", " ")


def tbl(data, widths, header=True, font=7.2):
    converted = [[p(str(v), "SmallRU") for v in row] for row in data]
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0,0), (-1,-1), "DejaVu"), ("FONTSIZE", (0,0), (-1,-1), font),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B8C6CF")),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS", (0,1 if header else 0), (-1,-1), [colors.white, colors.HexColor("#F6F9FA")]),
    ]
    if header:
        commands += [("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCECF3")), ("TEXTCOLOR", (0,0), (-1,0), BLUE), ("FONTNAME", (0,0), (-1,0), "DejaVu-Bold")]
    t.setStyle(TableStyle(commands)); return t


def command(text):
    return p(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>"), "MonoRU")


def shell(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


TMP.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

# Profile chart
fig, ax = plt.subplots(figsize=(7.2, 3.0))
engines = ["MapReduce", "DuckDB"]
times = [analysis["profile_summary"]["mapreduce"]["median_seconds"], analysis["profile_summary"]["duckdb"]["median_seconds"]]
bars = ax.bar(engines, times, color=["#168A8A", "#173B57"], width=.55)
ax.set_ylabel("Медиана времени, с"); ax.set_title("Время выполнения, 3 запуска")
ax.spines[["top","right"]].set_visible(False); ax.bar_label(bars, fmt="%.3f с", padding=3)
fig.tight_layout(); profile_chart = TMP / "profile.png"; fig.savefig(profile_chart, dpi=180); plt.close(fig)

# Combination chart, log scale
growth = analysis["combination_growth"]
fig, ax = plt.subplots(figsize=(7.2, 3.0))
labels = ["Навыки", "Пары", "Тройки"]; values = [growth["1"], growth["2"], growth["3"]]
bars = ax.bar(labels, values, color=["#6FA8B8", "#168A8A", "#173B57"])
ax.set_yscale("log"); ax.set_ylabel("Число уникальных комбинаций (log)"); ax.set_title("Комбинаторный рост")
ax.bar_label(bars, labels=[f"{v:,}".replace(","," ") for v in values], padding=3)
ax.spines[["top","right"]].set_visible(False); fig.tight_layout(); combo_chart = TMP / "combinations.png"; fig.savefig(combo_chart, dpi=180); plt.close(fig)

disk_output = shell(["docker", "exec", "lab3-rustfs", "du", "-sk", "/data1", "/data2", "/data3", "/data4"])
object_rows = json.loads(shell([str(ROOT/".venv/bin/python"), "-m", "src.storage", "list"]))
object_output = "\n".join(f"{row['size']:>10}  s3://hh-lake/{row['key']}" for row in object_rows)
container_output = shell(["docker", "ps", "--filter", "name=lab3-rustfs", "--format", "{{.Names}}  {{.Status}}  {{.Ports}}"])
retry_output = (ROOT / "artifacts/run-logs/mapreduce-failure-retry.log").read_text(encoding="utf-8").strip()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5DEE4")); canvas.line(18*mm, 14*mm, 192*mm, 14*mm)
    canvas.setFont("DejaVu", 7.5); canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 9*mm, "Лабораторная работа 3 - Технология MapReduce")
    canvas.drawRightString(192*mm, 9*mm, f"Страница {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(str(OUT_REPO), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=18*mm,
                      title="Лабораторная работа 3. Технология MapReduce", author="Дарья Сидельникова")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=footer))
story = []

story += [Spacer(1, 14*mm), p("Лабораторная работа 3", "TitleRU"), p("Технология MapReduce", "TitleRU"),
          Spacer(1, 7*mm), p("Вариант 11: DevOps-инженер", "Callout"),
          p("Студент: Сидельникова Дарья Николаевна<br/>Группа: ИИИ-3-ИнжДан-1-2<br/>Преподаватель: Артём Галимьянов<br/>Дата выполнения: 21 октября 2026 года", "Sub"),
          Spacer(1, 5*mm), p(f'<b>Репозиторий:</b> <link href="{REPOSITORY_URL}" color="#168A8A">{REPOSITORY_URL}</link>', "BodyRU"),
          Spacer(1, 16*mm), p("Цель", "H2RU"), p("Развернуть объектное хранилище RustFS, обработать один и тот же S3-объект собственной реализацией MapReduce и DuckDB, доказать совпадение результатов, измерить время и память, а затем получить практические выводы о навыках, зарплатах и регионах.")]

story += [PageBreak(), p("1. Исходные данные и условие варианта", "H1RU")]
story += [p(f"Исходный CSV занимает 847 619 384 байта и содержит {prepare['source_rows']:,} строк.".replace(","," ")),
          p("Для варианта использовано точное условие <b>role = 'DevOps-инженер'</b>. Поиск слова DevOps в названии не использовался: он захватывает системных инженеров, разработчиков и администраторов, поэтому нарушает индивидуальный вариант."),
          tbl([
              ["Показатель", "Значение"], ["Строк после фильтра", prepare["selected_rows"]],
              ["Со списком навыков", prepare["rows_with_skills"]], ["С зарплатой в RUR", prepare["rows_with_salary"]],
              ["Формат сегмента", "NDJSON, одна вакансия на строку"], ["Размер объекта", f"{prepare['output_bytes']:,} байт".replace(","," ")]
          ], [70*mm, 92*mm]), Spacer(1,4*mm),
          p("Правила очистки", "H2RU"),
          p("Навыки разделяются по точке с запятой, пробелы нормализуются, повторы внутри вакансии удаляются без учёта регистра. Сочетания сортируются и считаются один раз на вакансию. Зарплата учитывается только в RUR: для интервала берётся середина, для одной границы - имеющееся значение; net переводится в gross делением на 0,87. Вакансии без зарплаты участвуют в частотах, но не в медианах."),
          p("Команда подготовки", "H2RU"), command("$ .venv/bin/python -m src.prepare --input /Users/side/Downloads/it_vacancies_2024.csv\nselected_rows: 5158\nrows_with_skills: 3534\nrows_with_salary: 1037")]

story += [PageBreak(), p("2. RustFS и объект в hh-lake", "H1RU"),
          p("RustFS запущен в Docker в режиме Single Node Multiple Disk с четырьмя томами /data1 ... /data4. На Docker Desktop тома видны как один виртуальный блочный девайс, поэтому только для лаборатории включён RUSTFS_UNSAFE_BYPASS_DISK_CHECK. В производственной среде такой флаг использовать нельзя."),
          p("Состояние контейнера", "H2RU"), command("$ docker ps --filter name=lab3-rustfs\n" + container_output),
          p("Объекты бакета", "H2RU"), command("$ .venv/bin/python -m src.storage list\n" + object_output),
          p("Размеры четырёх дисков после загрузки исходного объекта и результатов", "H2RU"), command("$ docker exec lab3-rustfs du -sk /data1 /data2 /data3 /data4\n" + disk_output),
          p("Каждый том занимает одинаковые 47 664 KiB. Это ожидаемо для EC 2+2 на четырёх дисках: объект делится на два data-фрагмента и два parity-фрагмента. Код хранит 2 единицы полезных данных в 4 фрагментах, коэффициент избыточности равен 4/2 = 2. Разница между логическим размером объектов и du включает метаданные, малые объекты и размер блоков файловой системы."),
          p("Физическое ограничение", "H2RU"), p("RustFS видит четыре отдельных тома и распределяет между ними данные и фрагменты восстановления. Но все тома физически находятся внутри одного Docker Desktop на одном компьютере. Поэтому эксперимент показывает, как система переживает недоступность одного тома, но не защищает от поломки самого компьютера или общего диска. Для настоящей отказоустойчивости нужны разные физические диски, а лучше несколько серверов.")]

story += [PageBreak(), p("3. Собственная реализация MapReduce", "H1RU"),
          p("Драйвер получает размер объекта через HEAD, делит диапазон на чанки по 256 KiB и запускает четыре mapper-потока. Каждый mapper делает S3 Range GET. Границы выравниваются по переводу строки: запись принадлежит чанку, содержащему её первый байт. Mapper формирует локальные счётчики, reducer сливает их в детерминированном порядке."),
          tbl([["Этап", "Действие"], ["Map", "Чтение Range-чанка, разбор NDJSON, генерация C(n,1), C(n,2), C(n,3)"], ["Shuffle", "Ключ - отсортированный кортеж навыков"], ["Reduce", "Сумма частот и объединение выборок зарплат"], ["Output", "Три JSON-результата в s3://hh-lake/results/11-devops/"]], [31*mm,131*mm]),
          Spacer(1,4*mm), p("Контрольные числа", "H2RU"),
          tbl([["Размер стека", "Уникальных ключей"], ["1 навык", f"{growth['1']:,}".replace(","," ")], ["2 навыка", f"{growth['2']:,}".replace(","," ")], ["3 навыка", f"{growth['3']:,}".replace(","," ")]], [75*mm, 65*mm]),
          Image(str(combo_chart), width=164*mm, height=68*mm),
          p("Рост объясняется числом сочетаний внутри вакансии: для n навыков mapper создаёт n одиночных ключей, n(n-1)/2 пар и n(n-1)(n-2)/6 троек. Поэтому число потенциальных троек растёт кубически.")]

story += [PageBreak(), p("4. DuckDB и независимая верификация", "H1RU"),
          p("DuckDB подключается к тому же объекту s3://hh-lake/variants/11-devops/vacancies.ndjson через расширение httpfs. Массив skills раскрывается UNNEST ... WITH ORDINALITY. Пары и тройки формируются self join по возрастающим позициям, поэтому каждая комбинация учитывается один раз."),
          command("CREATE VIEW vacancies AS\nSELECT * FROM read_ndjson_auto('s3://hh-lake/variants/11-devops/vacancies.ndjson');\n\nCREATE VIEW expanded AS\nSELECT vacancy_id, area, salary_rur, skill, pos\nFROM vacancies, UNNEST(skills) WITH ORDINALITY AS t(skill, pos);"),
          p("Полная проверка", "H2RU"),
          tbl([["Проверка", "Результат"], ["Число вакансий", "5158 = 5158"], ["Вакансии с навыками", "3534 = 3534"], ["Навыки: частоты, salary_n, медианы", "Совпали"], ["Пары: частоты, salary_n, медианы", "Совпали"], ["Тройки: частоты, salary_n, медианы", "Совпали"]], [94*mm,68*mm]),
          Spacer(1,5*mm), p("Итог: <b>verification.passed = true</b>. Сравнивались не только итоговые суммы, а полные множества ключей и значений для всех трёх размеров стека.", "Callout"),
          p("Найденная и исправленная ошибка", "H2RU"), p("Первый запуск MapReduce дал 5 159 строк против 5 158 в DuckDB. Причина: строка на границе двух Range-чанков учитывалась дважды. После привязки записи к чанку по начальному байтовому смещению все таблицы совпали. Этот случай показывает практическую ценность независимого SQL-контроля.")]

story += [PageBreak(), p("5. Профилирование", "H1RU"),
          p("Каждый способ запущен три раза. Измерено реальное wall-clock время и максимальный RSS всего дерева процесса с частотой опроса 20 мс."),
          tbl([["Способ", "Попытка", "Время, с", "Пик RSS, MiB"]] + [[r["engine"], r["attempt"], f"{r['seconds']:.4f}", f"{r['peak_rss_mb']:.2f}"] for r in profile["runs"]], [48*mm,28*mm,38*mm,42*mm]),
          Spacer(1,5*mm), Image(str(profile_chart), width=164*mm, height=68*mm),
          p(f"Медиана MapReduce: {analysis['profile_summary']['mapreduce']['median_seconds']:.4f} с и {analysis['profile_summary']['mapreduce']['median_peak_rss_mb']:.2f} MiB. Медиана DuckDB: {analysis['profile_summary']['duckdb']['median_seconds']:.4f} с и {analysis['profile_summary']['duckdb']['median_peak_rss_mb']:.2f} MiB."),
          p("DuckDB быстрее примерно на 9%, но использует примерно на 24% больше памяти. На сегменте в 1,6 МБ накладные расходы планирования, HTTP и сериализации доминируют. Эти числа нельзя напрямую переносить на заявленные в задании 24 ГБ: там преимущества векторного SQL и ограничения памяти проявятся иначе.")]

story += [PageBreak(), p("6. Проверка отказа маппера", "H1RU"),
          p("Для проверки повторного выполнения чанк 0 намеренно завершается исключением. Драйвер перезапускает только упавший mapper и продолжает reduce."),
          command("$ .venv/bin/python -m src.mapreduce_job --simulate-failure\n" + retry_output),
          p("После повторного запуска retried_chunks = 1, число строк осталось 5 158. Повторная команда src.verify снова вернула passed = true для навыков, пар и троек.", "Callout"),
          p("Семантика", "H2RU"), p("Mapper не имеет побочных эффектов и выдаёт локальный аккумулятор, поэтому его повтор безопасен. Reducer запускается после завершения всех mapper-задач. Для промышленного решения потребовались бы лимит повторов, backoff, журнал причин отказа и промежуточные durable-результаты.")]

story += [PageBreak(), p("7. Региональный анализ", "H1RU"),
          p("Выбраны три региона с наибольшим числом вакансий, чтобы уменьшить нестабильность медиан."),
          tbl([["Регион", "Вакансий", "С зарплатой", "Медиана gross, RUR", "Топ-3 навыка"]] + [[r["region"], r["vacancies"], r["salary_n"], fmt_money(r["median_salary_rur"]), ", ".join(x["skills"][0] for x in r["top_skills"][:3])] for r in analysis["top_regions"]], [36*mm,22*mm,25*mm,32*mm,51*mm]),
          Spacer(1,6*mm),
          p("Наблюдения", "H2RU"),
          p("Москва концентрирует 3 007 вакансий, или 58,3% сегмента, и имеет медиану 287 356 RUR по 523 объявлениям с зарплатой. В Санкт-Петербурге медиана равна 230 000 RUR, в Екатеринбурге - 172 414 RUR. Во всех трёх регионах лидируют Linux, Docker и Kubernetes, но порядок различается: в Москве Kubernetes опережает Docker, а в Санкт-Петербурге и Екатеринбурге Docker находится выше."),
          p("Самая частая пара во всех трёх регионах - Docker + Kubernetes. Самая частая тройка - Docker + Kubernetes + Linux. Это указывает на единое ядро DevOps-стека, а не на регионально разные специализации."),
          p("Ограничение", "H2RU"), p("Зарплата указана только у части вакансий: 17,4% в Москве, 21,4% в Санкт-Петербурге и 21,8% в Екатеринбурге. Региональные медианы описывают объявления с раскрытой зарплатой и могут быть смещены относительно всего рынка.")]

def effect_rows(rows):
    return [["Комбинация", "n зарплат", "Медиана", "База", "Медиана базы", "Разница"]] + [[", ".join(x["skills"]), x["salary_n"], fmt_money(x["median_salary_rur"]), ", ".join(x["baseline_skills"]), fmt_money(x["baseline_median_salary_rur"]), fmt_money(x["delta_rur"])] for x in rows[:5]]

story += [PageBreak(), p("8. Влияние навыков на зарплату", "H1RU"),
          p("Для пары базой служит более частый из двух одиночных навыков. Для тройки - наиболее частая из трёх входящих пар. Сравниваются медианы только при наличии не менее 10 зарплат и у комбинации, и у базы. Это соответствует требованию не сравнивать редкую комбинацию с ещё более редкой базой."),
          p("Наибольшее повышение: пары", "H2RU"), tbl(effect_rows(analysis["pair_increase"]), [42*mm,18*mm,24*mm,33*mm,24*mm,24*mm]),
          Spacer(1,5*mm), p("Наибольшее понижение: пары", "H2RU"), tbl(effect_rows(analysis["pair_decrease"]), [42*mm,18*mm,24*mm,33*mm,24*mm,24*mm]),
          Spacer(1,5*mm), p("Интерпретация", "H2RU"),
          p("Связка DevOps + SRE показывает +170 115 RUR к медиане более частого DevOps, а Git + GitLab CI - +160 920 RUR к Git. Снижение у Ansible + Atlassian Jira и Ansible + Debian не означает причинного эффекта навыка: оно может отражать другой уровень позиций, отрасль, регион или особенности небольшой выборки.")]

story += [PageBreak(), p("9. Тройки навыков", "H1RU"),
          p("Наибольшее повышение: тройки", "H2RU"), tbl(effect_rows(analysis["triple_increase"]), [42*mm,18*mm,24*mm,33*mm,24*mm,24*mm]),
          Spacer(1,5*mm), p("Наибольшее понижение: тройки", "H2RU"), tbl(effect_rows(analysis["triple_decrease"]), [42*mm,18*mm,24*mm,33*mm,24*mm,24*mm]),
          Spacer(1,5*mm), p("Вывод", "H2RU"), p("CI/CD + ELK + Python и Git + GitLab CI + Linux имеют прибавку около 172 414 RUR к своим наиболее частым парным базам. Наблюдаемые различия полезны как гипотезы для поиска вакансий, но не доказывают, что добавление навыка само по себе повысит зарплату: данные наблюдательные, а зарплатные поля заполнены неполно.")]

story += [PageBreak(), p("10. Итоги и выбор инструмента", "H1RU"),
          p("Вывод", "H2RU"),
          p("На этом наборе данных мне удобнее использовать DuckDB. Запрос получается компактным, его проще проверить, а расчёт выполняется немного быстрее. Собственный MapReduce потребовал больше кода, зато на его примере хорошо видно весь процесс: чтение объекта частями, работа нескольких mapper-задач, объединение результатов и повтор упавшего чанка."),
          p("Если объём данных вырастет до десятков гигабайт, текущую реализацию MapReduce придётся доработать. Сейчас reducer хранит комбинации и списки зарплат в памяти. Для больших данных промежуточные результаты нужно частично записывать на диск и объединять поэтапно."),
          p("RustFS оказался удобным общим хранилищем для обоих способов расчёта: MapReduce и DuckDB читали один и тот же объект через S3 API. Четыре учебных тома показывают работу Erasure Coding, но для реальной системы я бы разместила данные на разных физических дисках или серверах, настроила резервное копирование, TLS и отдельную учётную запись для приложения."),
          p("Воспроизводимость", "H2RU"), command("$ cp .env.example .env\n$ make setup\n$ make up\n$ make prepare CSV=/absolute/path/to/it_vacancies_2024.csv\n$ make upload\n$ make profile\n$ make analyze\n$ .venv/bin/python -m src.storage upload-results")]

OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
OUT_USER.parent.mkdir(parents=True, exist_ok=True)
doc.build(story)
shutil.copy2(OUT_REPO, OUT_USER)
print(OUT_REPO)
print(OUT_USER)
