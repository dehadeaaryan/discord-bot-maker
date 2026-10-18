import io
import json
import zipfile

import pytest
from pydantic import ValidationError

from discord_bot_maker import BotDefinition, Context, Engine, FlowBot, Simulator, Settings
from discord_bot_maker.export import export_archive
from discord_bot_maker.templates import template


def definition(node, **trigger):
    data = template().model_dump(mode="json")
    data['nodes'][0].update(trigger)
    data['nodes'][1] = dict(id='reply-1', **node)
    return BotDefinition.model_validate(data)


def test_dual_arguments_policies_and_rich_embed():
    data = definition({'kind':'embed','title':'{{options.topic}}','fields':[{'name':'Status','value':'Ready'}], 'footer':'For {{user.display_name}}'}, mode='both', options=[{'name':'topic','type':'str','autocomplete':['Python','Discord']}], checks={'server_only':True,'roles':['99'],'permission':'manage_guild'})
    engine = Engine(data)
    with pytest.raises(ValueError, match='role'):
        engine.execute('hello',Context(),options={'topic':'Python'})
    context = Context(role_ids=['99'], permissions=['manage_guild'])
    result = engine.execute('hello',context,'prefix',options={'topic':'Python'})
    assert result['messages'][0]['fields'][0]['value']=='Ready'
    assert result['messages'][0]['title']=='Python'
    with pytest.raises(ValueError, match='Missing'):
        engine.execute('hello',context)


@pytest.mark.asyncio
async def test_export_runtime_uses_shared_prefix_and_slash_validation():
    data = definition({'kind':'reply','content':'{{options.count}}'},mode='both',options=[{'name':'count','type':'int'}])
    client = FlowBot(data,storage=':memory:')
    async with Simulator(client.dbm) as sim:
        assert (await sim.command('hello',options={'count':3})).content=='3'
        assert (await sim.command('hello',mode='prefix',arguments='4')).content=='4'
        assert 'Expected' in (await sim.command('hello',mode='prefix',arguments='x')).content
    await client.close()


@pytest.mark.asyncio
async def test_interactive_preview_and_live_callback_parity():
    data = definition({'kind':'message','content':'Pick','buttons':[{'label':'Hello','reply':'Hi {{options.name}}'}],'selects':[{'options':['One','Two'],'reply':'Picked {{input.value}}'}],'attachments':[{'filename':'test.txt','content':'For {{options.name}}'}]},options=[{'name':'name','type':'str'}])
    engine = Engine(data)
    result = engine.execute('hello',Context(),options={'name':'Sam'})
    assert result['messages'][0]['attachments'][0]['content']=='For Sam'
    clicked = engine.execute('hello',Context(),options={'name':'Sam'},component={'node_id':'reply-1','type':'select','index':0,'value':'Two'})
    assert clicked['messages'][0]['content']=='Picked Two'
    client = FlowBot(data,storage=':memory:')
    async with Simulator(client.dbm) as sim:
        sent = await sim.command('hello',options={'name':'Sam'})
        assert (await sim.click(sent)).content=='Hi Sam'
        assert (await sim.click(sent,1,value='Two')).content=='Picked Two'
    await client.close()


@pytest.mark.asyncio
async def test_forms_and_privacy_survive_runtime():
    data = definition({'kind':'form','title':'Feedback','response':'Received {{input.feedback}}'})
    client = FlowBot(data,storage=':memory:')
    async with Simulator(client.dbm) as sim:
        form = await sim.command('hello')
        assert form.modal.title=='Feedback'
        assert (await sim.submit(form,{'feedback':'Great'})).content=='Received Great'
    await client.close()
    private = FlowBot(definition({'kind':'reply','content':'Secret','ephemeral':True}),storage=':memory:')
    async with Simulator(private.dbm) as sim:
        result = await sim.command('hello')
        assert result.messages[0]['ephemeral'] is True
    await private.close()


def test_component_click_does_not_repeat_storage_actions():
    data = definition({'kind':'message','content':'Pick','buttons':[{'label':'Go','reply':'Clicked'}]}).model_dump(mode='json')
    data['nodes'].append({'kind':'action','id':'count','operation':'store_increment','key':'count','value':'1'})
    data['edges']=[{'id':'a','source':'command-1','target':'count'},{'id':'b','source':'count','target':'reply-1'}]
    engine=Engine(BotDefinition.model_validate(data))
    first=engine.execute('hello',Context())
    assert first['state']['values'][Context().server_id]['count']==1
    second=engine.execute('hello',Context(),component={'node_id':'reply-1','type':'button','index':0})
    assert second['state']['values'][Context().server_id]['count']==1
    assert second['messages'][0]['content']=='Clicked'


@pytest.mark.asyncio
async def test_jobs_ownership_and_packs_and_settings(tmp_path):
    data=definition({'kind':'action','operation':'schedule','value':'Hello later','response':'Done'}).model_dump(mode='json')
    data['runtime'].update(help=True,packs=['polls','reminders','moderation'],settings={'version':1,'defaults':{'greeting':'Welcome'}})
    client=FlowBot(BotDefinition.model_validate(data),storage=tmp_path/'bot.sqlite3')
    assert {'help','poll','remind','kick','ban','timeout'} <= {c.name for c in client.tree.get_commands()}
    async with Simulator(client.dbm) as sim:
        result=await sim.command('hello')
        job_id=result.content.removeprefix('Scheduled job: ')
        assert client.dbm.jobs.status(job_id)['status']=='pending'
        assert client.dbm.store.scope('visual-job-owner').get(job_id)==['1','10']
    await client.close()
    with zipfile.ZipFile(io.BytesIO(export_archive(BotDefinition.model_validate(data)))) as archive:
        assert json.loads(archive.read('bot.json'))['runtime']['help']
        assert b'>=2.1.1' in archive.read('requirements.txt')


@pytest.mark.parametrize('mutation',[
    lambda d:d['nodes'][0].update(mode='both'),
    lambda d:d['edges'].append({'id':'extra','source':'reply-1','target':'reply-1'}),
])
def test_invalid_forms_rejected(mutation):
    data=definition({'kind':'form'}).model_dump(mode='json')
    mutation(data)
    with pytest.raises(ValidationError):BotDefinition.model_validate(data)


def test_mode_collisions_and_pack_names_rejected():
    data=template().model_dump(mode='json')
    data['nodes'][0]['mode']='both'
    data['nodes'].append(dict(data['nodes'][0],id='other',mode='prefix'))
    data['edges'].append({'id':'other','source':'other','target':'reply-1'})
    with pytest.raises(ValidationError,match='unique'):BotDefinition.model_validate(data)
    data=template().model_dump(mode='json');data['runtime']['help']=True;data['nodes'][0]['name']='help'
    with pytest.raises(ValidationError,match='conflicts'):BotDefinition.model_validate(data)


@pytest.mark.asyncio
async def test_versioned_settings_actions_require_permissions_and_persist(tmp_path):
    data=definition({'kind':'action','operation':'setting_set','key':'greeting','value':'Welcome','response':'{{store.value}}'}).model_dump(mode='json')
    data['runtime']['settings']={'version':1,'defaults':{'greeting':'Hello'}}
    parsed=BotDefinition.model_validate(data)
    with pytest.raises(ValueError,match='manage server'):
        Engine(parsed).execute('hello',Context())
    engine=Engine(parsed)
    assert engine.execute('hello',Context(permissions=['manage_guild']))['messages'][0]['content']=='Welcome'
    read=template().model_dump(mode='json')
    read['nodes'][1]['content']='{{settings.greeting}}'
    read['runtime']['settings']=data['runtime']['settings']
    assert Engine(BotDefinition.model_validate(read),state=engine.state).execute('hello',Context())['messages'][0]['content']=='Welcome'
    client=FlowBot(parsed,storage=tmp_path/'settings.sqlite3')
    async with Simulator(client.dbm) as sim:
        assert (await sim.command('hello',permissions=('manage_guild',))).content=='Welcome'
        assert client.dbm.settings(10,Settings(1,{'greeting':'Hello'})).get()['greeting']=='Welcome'
    await client.close()


@pytest.mark.asyncio
async def test_legacy_distinct_prefix_and_slash_flows_keep_same_name():
    data=template().model_dump(mode='json')
    data['nodes'] += [dict(data['nodes'][0],id='prefix-hello',mode='prefix'),{'id':'prefix-reply','kind':'reply','content':'Prefix flow'}]
    data['edges'].append({'id':'prefix-edge','source':'prefix-hello','target':'prefix-reply'})
    client=FlowBot(BotDefinition.model_validate(data),storage=':memory:')
    assert client.tree.get_command('hello') is not None
    assert client.get_command('hello') is not None
    assert client.engine.execute('hello',Context(),'prefix')['messages'][0]['content']=='Prefix flow'
    await client.close()
