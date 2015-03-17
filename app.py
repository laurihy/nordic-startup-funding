import pystache
from jinja2 import Environment, FileSystemLoader
import table

env = Environment(
  loader=FileSystemLoader('./templates')
)

template = env.get_template('index.html')

def partial(template, **kwargs):
    return env.get_template(template).render(isinstance=type, **kwargs)

print template.render(
    by_year_and_location=table.by_year_and_location,
    by_year_and_series_and_location=table.by_year_and_series_and_location,
    top_investors=table.top_investors_by_location_and_year,
    top_companies=table.top_companies_by_location,
    top_founders=table.top_founders_by_location,
    x_axis=table.x_axis,
    partial=partial)




