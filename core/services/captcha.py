from core.captcha.anycaptcha import Service, Solver
from core.settings import settings


async def solve_recaptcha_v2(user_agent, key, url, is_invisible=False):
    service_cap = getattr(Service, settings.env.captcha_service)
    async with Solver(service_cap, settings.env.captcha_api_key) as solver:
        solved = await solver.solve_recaptcha_v2(
            site_key=key,
            page_url=url,
            is_invisible=is_invisible,
            user_agent=user_agent,
            api_domain='google.com'
        )
        code_solve_result = solved.solution.token
    return code_solve_result

async def solve_recaptcha_v3(user_agent, key, url):
    service_cap = getattr(Service, settings.env.captcha_service)
    async with Solver(service_cap, settings.env.captcha_api_key) as solver:
        solved = await solver.solve_recaptcha_v3(
            site_key=key,
            page_url=url,

            user_agent=user_agent,
            api_domain='google.com'
        )
        code_solve_result = solved.solution.token
    return code_solve_result
