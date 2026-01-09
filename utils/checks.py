import lightbulb as lb


@lb.Check
def trusted_user_check(ctx: lb.Context) -> bool:
    db = ctx.bot.d.con
    cursor = db.cursor()
    response = cursor.execute("""SELECT user_id FROM trusted_users""")

    trusted_users = ctx.bot.owner_ids
    trusted_users += response.fetchall()

    return ctx.author.id in trusted_users
