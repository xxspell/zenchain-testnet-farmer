from core.captcha.anycaptcha import Service, Solver
from core.settings import settings


async def solve_recaptcha(user_agent):
    service_cap = getattr(Service, settings.env.captcha_service)
    async with Solver(service_cap, settings.env.captcha_api_key) as solver:
        solved = await solver.solve_recaptcha_v2(
            site_key=settings.app.captcha_website_key,
            page_url=settings.app.captcha_website_url,
            is_invisible=False,
            user_agent=user_agent,
            api_domain='google.com'
        )
        code_solve_result = solved.solution.token
    return code_solve_result