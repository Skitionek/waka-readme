'''
WakaTime progress visualizer
'''

# region Imports
import random
import re
import os
import base64
import sys
import datetime
from typing import Union

import requests
import math
from github import Github, GithubException, UnknownObjectException

# endregion

START_COMMENT = os.getenv('INPUT_START_COMMENT', '<!--START_SECTION:waka-->')
END_COMMENT = os.getenv('INPUT_END_COMMENT', '<!--END_SECTION:waka-->')
listReg = f"{START_COMMENT}[\\s\\S]+{END_COMMENT}"

user = os.getenv('INPUT_USERNAME')
waka_key = os.getenv('INPUT_WAKATIME_API_KEY')
ghtoken = os.getenv('INPUT_GH_TOKEN')
show_title = os.getenv("INPUT_SHOW_TITLE")
width = os.getenv('INPUT_WIDTH', 300)
height = os.getenv('INPUT_HEIGHT', 300)
colors_map_url = os.getenv('INPUT_COLORS_URL', "https://raw.githubusercontent.com/ozh/github-colors/master/colors.json")
svg_path = os.getenv('INPUT_SVG_PATH', 'waka_stats.svg')
waka_time_range = os.getenv('INPUT_WAKA_TIME_RANGE', 'last_7_days')

assert waka_time_range in ['last_7_days', 'last_30_days', 'last_6_months', 'last_year']

lang_colors = requests.get(colors_map_url).json()


def to_kebab_case(s: str) -> str:
	return re.sub(r'(?<!^)(?=[A-Z])', '-', s).lower()


def this_week() -> str:
	'''Returns a week streak'''
	week_end = datetime.datetime.today() - datetime.timedelta(days=1)
	week_start = week_end - datetime.timedelta(days=7)
	print("Week header created")
	return f"Week: {week_start.strftime('%d %B, %Y')} - {week_end.strftime('%d %B, %Y')}"


def html(tag: str, children: Union[str, tuple] = tuple(), **kwargs) -> str:
	args = ' '.join(
			f"{to_kebab_case(key)}='{value}'" if key != 'className' else f"class='{value}'"
				for key, value in kwargs.items()
	)
	rendered_children = children if isinstance(children, str) else '\n'.join(children)
	return f"<{tag} {args}>{rendered_children}</{tag}>"


def parse_lang_data(lang_data):
	lang_ent = []
	x = 0
	for index, lang in enumerate(lang_data):
		# following line provides a neat finish
		fmt_percent = format(lang['percent'], '0.2f').zfill(5)
		current_width = width * lang['percent'] / 100
		try:
			color = lang_colors[lang['name']]['color']
		except KeyError:
			color = random.choice(list(lang_colors.values()))['color']
		lang_ent.append(html(
				'rect',
				mask='url(#rect-mask)', dataTestid='lang-progress', x=x, y=0,
				width=current_width, height=8, fill=color
		))
		lang_ent.append(html('g',
				transform=f'translate({150 * (index % 2)}, {25 * math.ceil(index / 2)})',
				children=(
					html('circle',
							cx=5, cy=6, r=5, fill=color
					),
					html('text',
							dataTestid='lang-name', x=15, y=10, className='lang-name',
							children=f"{lang['name']} {lang['text']}({fmt_percent}%)"
					)
				)
		))
		x += current_width
		if index == 5:
			break
	return lang_ent


def get_stats(data=requests.get(
		f"https://wakatime.com/api/v1/users/current/stats/{waka_time_range}?api_key={waka_key}").json()) -> str:
	'''Gets API data and returns markdown progress'''
	
	try:
		lang_data = data['data']['languages']
	except KeyError:
		print("Please Add your WakaTime API Key to the Repository Secrets")
		sys.exit(1)
	
	print(lang_data)
	
	return '\n'.join(parse_lang_data(lang_data))


def decode_svg(data: str) -> str:
	'''Decode the contents of old readme'''
	decoded_bytes = base64.b64decode(data)
	return str(decoded_bytes, 'utf-8')


def generate_new_svg(stats: str) -> str:
	'''Generate a new svg'''
	return html('svg', xmlns="http://www.w3.org/2000/svg", width=350, height=170, viewBox="0 0 350 170",
			fill="none",
			children=(
				html('style', children="""
                    .header {
                        font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
                        fill: #2f80ed;
                        animation: fadeInAnimation 0.8s ease-in-out forwards;
                    }
                    .lang-name {
                        font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif;
                        fill: #333;
                    }
                """),
				html('rect',
						dataTestid="card-bg", x=0.5, y=0.5, rx=4.5, height="99%", stroke="#E4E2E2", width=349,
						fill="#fffefe", strokeOpacity=1
				),
				html('g', dataTestid="card-title", transform="translate(25, 35)", children= \
					html('g', transform="translate(0, 0)", children= \
						html('text', x=0, y=0, className="header", dataTestid="header",
								children='Most Used Languages'
						)
					)
				),
				html('g', dataTestid="main-card-body", transform="translate(0, 55)", children= \
					html('svg', dataTestid="lang-items", x=25, children=(
						html('mask', id="rect-mask", children= \
							html('rect', x=0, y=0, width=300, height=8, fill="white", rx=5)
						),
						START_COMMENT,
						stats,
						END_COMMENT
					)),
				)
			))


def substitute_svg_part(stats: str, svg: str) -> str:
	'''Generate a new svg'''
	stats_in_readme = f"{START_COMMENT}\n{stats}\n{END_COMMENT}"
	return re.sub(listReg, stats_in_readme, svg)


if __name__ == '__main__':
	g = Github(ghtoken)
	try:
		repo = g.get_repo(f"{user}/{user}")
	except GithubException:
		print(
				"Authentication Error. Try saving a GitHub Token in your Repo Secrets or Use the GitHub Actions "
				"Token, "
				"which is automatically used by the action."
		)
		sys.exit(1)
	
	waka_stats = get_stats()
	try:
		contents = repo.get_contents(svg_path)
		svg = decode_svg(contents.content)
		new_svg = substitute_svg_part(stats=waka_stats, svg=svg)
		if new_svg != svg:
			repo.update_file(
					path=contents.path,
					message='Updated with Dev Metrics',
					content=new_svg,
					sha=contents.sha,
					branch='master'
			)
	except UnknownObjectException:
		new_svg = generate_new_svg(stats=waka_stats)
		repo.create_file(
				path=svg_path,
				message='Updated with Dev Metrics',
				content=new_svg,
				branch='master'
		)
