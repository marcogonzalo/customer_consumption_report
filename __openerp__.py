# -*- coding: utf-8 -*-
##############################################################################
#
#    Customer consumption report module for Dentaltix ERP
#
##############################################################################

{
	'name': 'Dentaltix - Customer consumption report',
	'version': '1.0',
	'summary': 'Show a report about customers behavior in terms of sales invoiced',
	'author': '@MarcoGonzalo',
	'category' : 'Advanced Reporting',
	'description': """	
		Shows a report about customer behavior in terms of: 
			- Customer purchasing frequency
			- Average amount (untaxed)
			- Customer activity status

		Generate customer levels depending on number of invoices and average amount in the last year.
	""",
	'depends': ['base', 'account', 'sale', 'sale_crm'],
	'data': [
		'views/customer_consumption_report_views.xml'
	],
	'installable': True,
}