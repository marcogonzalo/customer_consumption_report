# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _
import openerp.addons.decimal_precision as dp

#Import logger
import logging
#Get the logger
_logger = logging.getLogger(__name__)

CUSTOMER_STATUSES = [
 	('activo', 'Active'),
	('inactivo', 'Inactive'),
]
CUSTOMER_LEVELS = [
 	('oro', 'Gold'),
	('plata', 'Silver'),
	('bronce', 'Bronze'),
	('turista', 'Tourist'),
]

class customer_consumption_report(models.Model):
	_name = 'customer_consumption_report'
	_description = 'Customer consumption report'
	_auto = False
	_order = 'display_name ASC'


	@api.depends('days_since_last_invoice','days_between_purchases','range_of_days')
	def _get_delay(self):
		for r in self:
			return ((r.days_between_purchases + r.range_of_days) - r.days_since_last_invoice)

	# If the customer has not genereated a new purchase before 30 days after hist/her maximum time of waiting
	# will be marked as inactive, until the next purchase. 
	def _set_customer_status(self):
	    for rec in self:
			rec.customer_status = 'active' if rec._get_delay() + 30 >= 0 else 'inactive'

	display_name = fields.Char('Partner', readonly=True)
	email = fields.Char('E-mail', readonly=True)
	phone = fields.Char('Phone number', readonly=True)
	total_invoices = fields.Integer('Total invoices', readonly=True)
	avg_amount = fields.Float('Average amount', digits_compute= dp.get_precision('Product Price'), readonly=True)
	total_amount = fields.Float('Total amount', digits_compute= dp.get_precision('Product Price'), readonly=True)
	date_first_invoice = fields.Date('Date of first invoice', readonly=True)
	date_last_invoice = fields.Date('Date of last invoice', readonly=True)
	days_between_purchases = fields.Integer('Days between purchases', readonly=True)
	range_of_days = fields.Integer('Range of days', readonly=True)
	days_since_last_invoice = fields.Integer('Days since last invoice', readonly=True)
	customer_status = fields.Selection(CUSTOMER_STATUSES, string='Status', readonly=True)
	customer_level = fields.Selection(CUSTOMER_LEVELS, string='Level', readonly=True)
	last_contact = fields.Date('Last contact', readonly=True)

	def init(self, cr):
		tools.sql.drop_view_if_exists(cr, 'customer_consumption_report')
		rs = cr.execute("""
			CREATE OR REPLACE VIEW customer_consumption_report AS (
				SELECT l.id, l.display_name, l.email, l.phone, l.total_invoices, l.avg_amount, l.total_amount, 
						l.date_first_invoice, l.date_last_invoice, l.days_between_purchases, l.range_of_days,
						(current_date - l.date_last_invoice) AS days_since_last_invoice, l.last_contact,
					(CASE WHEN (l.days_between_purchases + l.range_of_days - (current_date - l.date_last_invoice)) + 30 >= 0 THEN
						'activo'
					ELSE
						'inactivo'
					END) AS customer_status,
					(CASE WHEN l.sum_invoices_last_year >= 4 AND l.avg_amount_last_year > 200 THEN
							'oro'
						WHEN l.sum_invoices_last_year >= 4 AND l.avg_amount_last_year <= 200 THEN
							'plata'
						WHEN l.sum_invoices_last_year < 4 AND l.avg_amount_last_year > 200 THEN
							'bronce'
						ELSE
							'turista'
					END) AS customer_level
				FROM (
					SELECT rp.id, rp.display_name, rp.phone, rp.email, SUM(i.invoices_in_date) AS total_invoices,
							round(AVG(i.total_untaxed_per_day),2) AS avg_amount, SUM(i.total_untaxed_per_day) AS total_amount, 
							MIN(i.date_invoice) AS date_first_invoice, MAX(i.date_invoice) AS date_last_invoice, 
							extract(
								day from date_trunc('day', (
									CASE WHEN COUNT(*) <= 1 THEN 
										0 
									ELSE 
										SUM(time_since_last_invoice)/(COUNT(*)-1) 
									END
								) * '1 day'::interval)
							) AS days_between_purchases, 
							extract(
								day from date_trunc('day', (
									CASE WHEN COUNT(*) <= 2 THEN 
										0 
									ELSE 
										STDDEV(time_since_last_invoice) 
									END
								) * '1 day'::interval)
							) AS range_of_days,
							SUM(i.invoices_in_date) FILTER(WHERE i.date_invoice > NOW() - INTERVAL '1 year') AS sum_invoices_last_year,
							AVG(i.total_untaxed_per_day) FILTER(WHERE i.date_invoice > NOW() - INTERVAL '1 year') AS avg_amount_last_year,
							AVG(i.total_avg_amount_last_year),
							MAX(pc.date::DATE) AS last_contact
					FROM (
						SELECT ai.partner_id, ai.date_invoice, SUM(ai.amount_untaxed) AS total_untaxed_per_day, 
								COUNT(ai.partner_id) AS invoices_in_date, COALESCE(
									ai.date_invoice - lag(ai.date_invoice) OVER (
										PARTITION BY ai.partner_id ORDER BY ai.partner_id, ai.date_invoice 
										ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING
									), 0
								) AS time_since_last_invoice,
								AVG(ai.amount_untaxed) FILTER(WHERE ai.date_invoice > NOW() - INTERVAL '1 year') OVER () total_avg_amount_last_year
						FROM account_invoice AS ai 
						WHERE type = 'out_invoice' AND state IN ('open','paid') AND amount_untaxed > 0 AND amount_total > 0 
						GROUP BY ai.partner_id, ai.date_invoice, ai.amount_untaxed
						ORDER BY ai.partner_id, ai.date_invoice
					) AS i
					JOIN res_partner AS rp ON rp.id = i.partner_id
					LEFT JOIN crm_phonecall pc ON pc.partner_id = i.partner_id
					WHERE rp.customer = 't'
					GROUP BY rp.id
				) AS l
			); 
			SELECT * FROM customer_consumption_report;
		""")

customer_consumption_report()