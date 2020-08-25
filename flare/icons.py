"""
Generic icon handling, especially of embedded SVG images served from a pool of icons.
"""


import logging, string, os

from . import html5
from .config import conf
from .network import NetworkService


def fetchIconsFromJSON(url, then=None):
	"""
	Utility function that is used to fetch icons from an URL using NetworkRequest,
	and adding these icons to the icon pool.
	"""
	if then:
		then()
	return
	def _fetchIconsSuccess(req):
		try:
			icons = NetworkService.decode(req)
			assert isinstance(icons, dict)
			#conf["icons.pool"].update(icons)
		except Exception as e:
			logging.error("Error while parsing icons fetched from %r", url)
			logging.exception(e)

		if then:
			then()

	def _fetchIconsFailure(req, code):
		logging.error("Error %r while trying to fetch icons from %r", code, url)

		if then:
			then()

	logging.info("Starting to fetch icons from %r", url)

	NetworkService.request(
		None, url,
		successHandler=_fetchIconsSuccess,
		failureHandler=_fetchIconsFailure
	)

def getIconHTML(icon, classList=None):
	"""
	Retrieve SVG/HTML-code for icon, either from conf["icons.pool"] or a generated <i>-Tag
	"""
	classList = " ".join(classList) if classList else ""
	#todo visibility class
	#language=HTML
	return """<img src="/static/svgs/%s.svg" class="js-svg %s" style="visibility:hidden">""" % (icon, classList)




def svgReplacer(e):
	targetElem = e.target  # Element that just loaded
	def nsServiceSuccess(ns):  # We've fetched the svg from the server
		if targetElem.parentElement:  # Ignore if it disappeared from the DOM
			tmp = html5.domCreateElement("div")
			tmp.innerHTML = ns.result
			svgElem = tmp.querySelector("svg")
			for cls in [x for x in targetElem.classList if x != "js-svg"]:
				svgElem.classList.add(cls)
			svgElem.style.pointerEvents = "none"
			targetElem.parentElement.insertBefore(svgElem, targetElem)
			targetElem.parentElement.removeChild(targetElem)
	if targetElem.classList.contains("js-svg"):  # Start replacing only if we encountered an image with js-svg
		NetworkService.request(None, e.target.src, successHandler=nsServiceSuccess)


html5.document.addEventListener("load", svgReplacer, True)

@html5.tag
class Icon(html5.Div):
	"""
	The Icon-widget & tag either loads an icon from the icon pool
	or generates a dummy icon from the first letter.

	The icon pool can be loaded by fetchIconsFromJSON.
	"""

	def __init__(self, embedsvg=None, icon=None):
		super().__init__()
		self.embedsvg = None
		self.icon = None

		if embedsvg:
			self["embedsvg"] = embedsvg

		if icon:
			self["icon"] = icon

	def _setEmbedsvg(self, embedsvg):
		self.removeAllChildren()
		if not embedsvg:
			return

		self.embedsvg = embedsvg
		self.appendChild(getIconHTML(embedsvg))

	def _getEmbedsvg(self):
		return self.embedsvg

	def _setIcon(self, icon):
		self["embedsvg"] = icon
		self.icon = icon

		if icon:
			self.addClass("icon-wrap")
		else:
			self.removeClass("icon-wrap")

	def _getIcon(self):
		return self.icon

@html5.tag
class Noci(html5.I):
	"""
	Next-generation icon component:
	Represents either an image, or an icon or a placeholder text using an <i>-tag.
	"""
	_leafTag = True

	def __init__(self):
		super().__init__()
		self.fallback = None
		self.value = None
		self.badge = None
		self._badge = None
		self.baseclass = None

		self["baseclass"] = "i"

	def _setBaseclass(self, baseclass):
		if self.baseclass:
			self.removeClass(self.baseclass)

		self.baseclass = baseclass
		self.addClass(self.baseclass)

	def _getBaseclass(self):
		return self.baseclass

	def _setFallback(self, fallback):
		self.fallback = fallback
		self["value"] = self["value"]

	def _getFallback(self):
		return self.fallback

	def _setBadge(self, badge):
		self.badge = badge
		self._badge = html5.fromHTML("""<span class="badge"></span>""")[0]
		self._badge.appendChild(self.badge, replace=True)
		self["value"] = self["value"]

	def _getBadge(self):
		return self.badge

	def _setValue(self, value):
		self.removeAllChildren()
		self.element.innerHTML = ""

		self.value = value

		# Accept empty value
		if not value:
			if self.fallback:
				self["value"] = self.fallback

			return

		# Accept a fileBone entry
		elif isinstance(value, dict):
			self.appendChild(
				html5.Img(value.get("dest", {}).get("downloadUrl") or self.fallback)
			)
		# Accept a string containing a path
		elif isinstance(value, str) and "/" in value and os.path.splitext(value)[1].lower() in (".jpg", ".jpeg", ".gif", ".png", ".svg"):
			self.appendChild(
				html5.Img(value)
			)
		elif isinstance(value, str):
			#we need a better detection
			if value.startswith("icon-") or value.startswith("logo-"):
				self.appendChild(getIconHTML(value))
			else:
				value = value.replace("-", " ") # replace dashes by spaces
				value = value.translate({ord(c): None for c in string.punctuation})  # remove all punctuations

				self.appendChild("".join([tag[0] for tag in value.split(maxsplit=1)])) # Only allow first two words

		else:
			raise ValueError("Either provide fileBone-dict or string")

		if self.badge:
			self.appendChild(self._badge)

	def _getValue(self):
		return self.value
