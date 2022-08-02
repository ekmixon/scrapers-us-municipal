from pupa.scrape import Bill
from .utils import Urls, StlScraper
import time


class StLouisBillScraper(StlScraper):

	def scrape(self):
		for session in self.jurisdiction.legislative_sessions:
			session_id = session["identifier"]
			session_url = self.bill_session_url(session_id)
			page = self.lxmlize(session_url)
			# bills are in a <table class="data stripped"> 
			bill_rows = page.xpath("//table[contains(@class, 'data')]/tr")
			# first row is headers, so ignore it
			bill_rows.pop(0)
			
			for row in bill_rows:
				id_link = row.xpath("td[1]/a")[0]
				bill_id = id_link.xpath("text()")[0]
				bill_url = id_link.xpath("@href")[0]
				yield self.scrape_bill(bill_url, bill_id, session_id)


	def scrape_bill(self, bill_url, bill_id, session_id):
		page = self.lxmlize(bill_url)
		# create bill
		title = page.xpath("//h1/text()")[0]
		bill = Bill(identifier=bill_id,
			        legislative_session=session_id,
			        title=title)
		bill.add_source(bill_url, note="detail")

		# add additional fields

		# abstract
		try:
			# abstract is directly above <h2>Legislative History</h2>
			leg_his = page.xpath("//h2[text()='Legislative History']")[0]
			abstract = leg_his.xpath("preceding-sibling::p/text()")[0]
			bill.add_abstract(abstract=abstract.strip(), note="summary")
			# TODO trim whitespace from summary
		except IndexError:
			print(f"No abstract for bill {bill_id} in session {session_id}")

		# the rest of the fields are found inside this <table>
		data_table = page.xpath("//table[contains(@class, 'data')]")[0]

		# sponsor
		sponsor_name = data_table.xpath(self.bill_table_query("Sponsor") + "/text()")[0]
		bill.add_sponsorship(name=sponsor_name,
				classification="Primary",
				entity_type="person",
				primary=True
				)

		# actions
		action_lines = data_table.xpath(self.bill_table_query("Actions") + "/text()")
		for line in action_lines:
			line = line.join('')
			try:
				for date_str, action_type in self.parse_actions(line):
					bill.add_action(date=date_str,
						description=action_type,	
						classification=action_type)
			except ValueError:
				print(f"failed to parse these actions: {[line]}")


		# co-sponsors
		co_sponsors = data_table.xpath(self.bill_table_query("Co-Sponsors") + "/text()")
		co_sponsors = [name.strip() for name in co_sponsors if name.strip()]
		for name in co_sponsors:
			bill.add_sponsorship(name=name,
						classification="co-sponsor",
						entity_type="person",
						primary=False)

		# committee (stored as another sponsorship in OCD)
		committees = data_table.xpath(self.bill_table_query("Committee") + "/a/text()")
		for comm in committees:
			bill.add_sponsorship(name=comm,
							classification="secondary", # classification ?
							entity_type="organization",
							primary=False)

		return bill


	def bill_table_query(self, key):
		return f"//th[text()='{key}:']/../td"

	def bill_session_url(self, session_id):
		return f"{Urls.BILLS_HOME}?sessionBB={session_id}"

	def parse_actions(self, action_line):
		"""
		input will look like:
		'\n05/15/2015 Second Reading '

		return a tuple that looks like:
		('2015-05-15', 'reading-2')
		"""

		# date is the first word, rest of words describe the bill actions
		date_str, _, action_types_str = action_line.strip().partition(" ")

		# convert date format from eg "05/12/2015" to "2015-05-12"
		date = time.strptime(date_str, "%m/%d/%Y")
		date_str = time.strftime("%Y-%m-%d", date)

		# action_types_str might contain multiple action_types, eg
		# "Third Reading,Perfection"
		action_types = action_types_str.split(",")

		for act in action_types:
			# try to convert st louis phrase to OCD phrase, eg
			# "Second Reading" --> "reading-2"
			try:
				classification = self.action_classifications[act]
			except KeyError:
				print(act)
				raise ValueError(f"invalid bill action classification: {act}")
			# yield a result for each action_type
			yield date_str, classification
			
	action_classifications = {
		"First Reading": "reading-1",
		"Second Reading": "reading-2",
		"Third Reading": "reading-3",
		# TODO other cases. 
		# See http://docs.opencivicdata.org/en/latest/scrape/bills.html

		# what does "Perfection" map to?
		"Perfection": "referral", # ???

		# what does "Informal Calendar" map to?
		"Informal Calendar": "filing", # ???
	}