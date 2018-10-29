import graphene


class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))

    def resolve_hello(self, _info, name):
        return 'Hello ' + name


schema = graphene.Schema(query=Query)
