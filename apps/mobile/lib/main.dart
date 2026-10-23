import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api.dart';

void main() => runApp(const SwingApp());

const bg = Color(0xFF090F19);
const panel = Color(0xFF111E2C);
const secondary = Color(0xFF94A7BA);
const mint = Color(0xFF5BDFBC);
const amber = Color(0xFFEEC77B);

class SwingApp extends StatelessWidget {
  const SwingApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Swing Intelligence', debugShowCheckedModeBanner: false,
    theme: ThemeData(brightness: Brightness.dark, useMaterial3: true,
      scaffoldBackgroundColor: bg, colorScheme: ColorScheme.fromSeed(
          seedColor: mint, brightness: Brightness.dark, surface: panel),
      appBarTheme: const AppBarTheme(backgroundColor: bg, centerTitle: false),
      cardTheme: const CardThemeData(color: panel, margin: EdgeInsets.symmetric(vertical: 6))),
    home: const Shell(),
  );
}

class Shell extends StatefulWidget {
  const Shell({super.key});
  @override State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int tab = 0;
  late final SwingApi api;
  List<Map<String, dynamic>> opportunities = [];
  List<Map<String, dynamic>> watchlist = [];
  List<Map<String, dynamic>> journal = [];
  Map<String, dynamic> meta = {};
  String? error;
  bool loading = true;
  String market = 'ALL', strategy = 'BOTH';
  bool showExcluded = false;
  double minimumScore = 0;
  final search = TextEditingController();

  @override void initState() {
    super.initState();
    api = SwingApi(baseUrl: 'http://10.0.2.2:8000');
    _initialize();
  }
  Future<void> _initialize() async {
    final prefs = await SharedPreferences.getInstance();
    api.baseUrl = prefs.getString('base_url') ?? 'http://10.0.2.2:8000';
    await refresh();
  }
  @override void dispose() { search.dispose(); super.dispose(); }

  Future<void> refresh() async {
    setState(() { loading = true; error = null; });
    try {
      final a = await api.opportunities();
      final w = await api.watches();
      final j = await api.journal();
      final m = await api.call('/meta');
      if (!mounted) return;
      setState(() { opportunities = a; watchlist = w; journal = j; meta = m; loading = false; });
    } catch (e) { if (mounted) setState(() { error = e.toString(); loading = false; }); }
  }

  Future<void> _runScan() async {
    setState(() => loading = true);
    try { await api.scan(); await refresh(); } catch (e) { if (mounted) {
      setState(() { error = e.toString(); loading = false; });
      _snack(e.toString());
    } }
  }
  void _snack(String message) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }
  Future<void> _settings() async {
    final saved = await showDialog<bool>(context: context,
      builder: (_) => _ConnectionDialog(api: api, onError: _snack));
    if (saved == true) await refresh();
  }

  @override Widget build(BuildContext context) {
    final count = opportunities.length;
    return Scaffold(
      appBar: AppBar(title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(['OVERVIEW','OPPORTUNITY EXPLORER','WATCHLIST','TRADE JOURNAL'][tab],
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
        Text('${meta['mode']?.toString().toUpperCase() ?? 'OFFLINE'} · LONG ONLY · PRIVATE',
            style: const TextStyle(color: mint, fontSize: 10, letterSpacing: 1.2)),
      ]), actions: [IconButton(tooltip: 'Backend settings', onPressed: _settings, icon: const Icon(Icons.settings_outlined)),
          IconButton(tooltip: 'Refresh data', onPressed: loading ? null : refresh, icon: const Icon(Icons.refresh))]),
      body: loading ? const Center(child: CircularProgressIndicator())
        : error != null ? _failure()
        : RefreshIndicator(onRefresh: refresh, child: ListView(padding: const EdgeInsets.all(16), children: [
           _notice(), const SizedBox(height: 12),
           if (tab == 0) ..._home(count),
           if (tab == 1) ..._explore(),
           if (tab == 2) ..._watches(),
           if (tab == 3) ..._journal(),
           const SizedBox(height: 36)
        ])),
      bottomNavigationBar: NavigationBar(selectedIndex: tab, onDestinationSelected: (v) => setState(() => tab = v),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Explore'),
          NavigationDestination(icon: Icon(Icons.star_border), label: 'Watchlist'),
          NavigationDestination(icon: Icon(Icons.menu_book_outlined), label: 'Journal'),
        ]),
      floatingActionButton: tab == 0 || tab == 1 ? FloatingActionButton.small(
        tooltip: 'Run daily scan', onPressed: _runScan, child: const Icon(Icons.radar)) : null,
    );
  }

  Widget _failure() => Center(child: Padding(padding: const EdgeInsets.all(24), child:
    Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      const Icon(Icons.wifi_off, size: 48, color: amber), const SizedBox(height: 16),
      const Text('Backend unavailable', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
      const SizedBox(height: 12), Text(error ?? '', textAlign: TextAlign.center, style: const TextStyle(color: secondary)),
      const SizedBox(height: 20), FilledButton(onPressed: _settings, child: const Text('Configure connection')),
    ])));

  Widget _notice() => Container(padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: const Color(0xFF362A1D), borderRadius: BorderRadius.circular(9)),
      child: Text(meta['mode'] == 'demo'
       ? 'SYNTHETIC DEMO — harga bukan data pasar. Probabilitas dan eksekusi NOT VALIDATED.'
       : 'EXTERNAL EOD — feed belum memverifikasi aturan eksekusi. NOT FINANCIAL ADVICE.',
       style: const TextStyle(fontSize: 11, color: amber)));

  List<Widget> _home(int count) {
    final liquid = opportunities.where((x) => _liquid(x)).length;
    final sorted = <Map<String,dynamic>>[];
    for (final marketName in ['US','IDX','CRYPTO']) {
      final group = opportunities.where((x) => _liquid(x) && x['market']==marketName).toList()
        ..sort((a,b) => _score(b).compareTo(_score(a)));
      final seen = <String>{};
      for (final item in group) {
        if (seen.add(item['instrument_id'].toString()) && seen.length<=3) sorted.add(item);
      }
    }
    return [const SizedBox(height: 7), const Text('Trading cockpit.',style: TextStyle(fontSize: 28,fontWeight: FontWeight.bold)),
      const Text('Explore setups, study risks, keep your original evidence.',style: TextStyle(fontSize: 12,color: secondary)),
      const SizedBox(height: 20), Row(children: [
        Expanded(child:_kpi('SCANNED', '$count', 'Research candidates')),
        const SizedBox(width: 10), Expanded(child:_kpi('LIQUID', '$liquid', 'Historical gate pass'))]),
      const SizedBox(height: 20), const Text('Markets at a glance',style: TextStyle(fontSize: 17,fontWeight: FontWeight.bold)),
      const SizedBox(height: 8),
      ...['US','IDX','CRYPTO'].map((m) => Card(child: ListTile(
        title: Text(m), subtitle: const Text('Research signal count — not probabilities'),
        trailing: Text('${opportunities.where((x) => x['market']==m).length}',
            style: const TextStyle(fontSize: 24, color: mint, fontWeight: FontWeight.bold)),
        onTap: () { market=m; setState(() => tab=1); }))),
      const SizedBox(height: 16), const Text('Balanced research shortlist',style: TextStyle(fontSize: 17,fontWeight: FontWeight.bold)),
      ...sorted.take(8).map(_assetTile)
    ];
  }
  Widget _kpi(String label,String value,String note) => Container(padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color:panel,borderRadius:BorderRadius.circular(12)),
    child: Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Text(label,style:const TextStyle(color:secondary,fontSize:11)),const SizedBox(height:10),
      Text(value,style:const TextStyle(fontSize:28,fontWeight:FontWeight.bold,color:mint)),
      Text(note,style:const TextStyle(color:secondary,fontSize:10))]));

  List<Widget> _explore() {
    final filtered=opportunities.where((x) => (market=='ALL'||x['market']==market) &&
      (strategy=='BOTH'||(x['setup'] as Map)['strategy']==strategy) &&
      _score(x)>=minimumScore && (showExcluded || _liquid(x)) &&
      '${x['symbol']} ${x['name']}'.toLowerCase().contains(search.text.toLowerCase())).toList();
    return [const SizedBox(height: 8), const Text('Opportunity Explorer',style:TextStyle(fontSize:26,fontWeight:FontWeight.bold)),
      const SizedBox(height: 10),
      DropdownButtonFormField<String>(value:market,decoration:const InputDecoration(labelText:'Market'),
        items:['ALL','US','IDX','CRYPTO'].map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),
        onChanged:(x)=>setState(()=>market=x??'ALL')),
      const SizedBox(height:8),
      DropdownButtonFormField<String>(value:strategy,decoration:const InputDecoration(labelText:'Strategy'),
        items:['BOTH','PULLBACK','BREAKOUT'].map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),
        onChanged:(x)=>setState(()=>strategy=x??'BOTH')),
      const SizedBox(height:8), TextField(controller:search,onChanged:(_)=>setState((){}),decoration:const InputDecoration(labelText:'Search symbol',prefixIcon:Icon(Icons.search))),
      const SizedBox(height:8), Text('Minimum setup score: ${minimumScore.toInt()}'),
      Slider(value:minimumScore,min:0,max:100,divisions:20,onChanged:(v)=>setState(()=>minimumScore=v)),
      SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Include excluded / illiquid assets'), subtitle: const Text('Research only; default shows Liquid Universe'), value: showExcluded, onChanged: (v) => setState(() => showExcluded = v)),
      Text('${filtered.length} results · comparable only within market/strategy',style:const TextStyle(color:secondary,fontSize:11)),
      ...filtered.map(_assetTile),
      if(filtered.isEmpty)const Padding(padding:EdgeInsets.all(24),child:Text('No matches. Relax filters to see more.',textAlign:TextAlign.center)),
      OutlinedButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>BuilderPage(api:api))),
        icon:const Icon(Icons.tune),label:const Text('Custom Screener Builder'))
    ];
  }

  bool _liquid(Map<String,dynamic> x) => (x['liquidity'] as Map)['historical']=='PASS';
  int _score(Map<String,dynamic> x)=> ((x['setup'] as Map)['score'] as num).toInt();
  Widget _assetTile(Map<String,dynamic> x) {
    final setup = x['setup'] as Map;
    final status = setup['status'].toString();
    return Card(child: ListTile(onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>AssetPage(api:api,data:x,onWatch:refresh))),
      contentPadding:const EdgeInsets.symmetric(horizontal:13,vertical:5),
      leading:CircleAvatar(backgroundColor:const Color(0xFF1D3440),child:Text(x['symbol'].toString().substring(0,math.min(2,x['symbol'].toString().length)),style:const TextStyle(fontSize:11,color:mint))),
      title:Text(x['symbol'].toString(),style:const TextStyle(fontWeight:FontWeight.bold)),
      subtitle:Text('${x['market']} · ${setup['strategy']}\n$status · ${x['data_status']}',style:const TextStyle(fontSize:11,color:secondary)),
      isThreeLine:true,
      trailing:Column(mainAxisAlignment:MainAxisAlignment.center,children:[Text('${setup['score']}',style:const TextStyle(fontSize:22,color:mint,fontWeight:FontWeight.bold)),const Text('SQS / 100',style:TextStyle(fontSize:9,color:secondary))])
    ));
  }
  List<Widget> _watches(){ final ids=watchlist.map((x)=>x['instrument_id']).toSet();final rows=opportunities.where((x)=>ids.contains(x['instrument_id'])).toList();return [
    const Text('Personal watchlist',style:TextStyle(fontSize:26,fontWeight:FontWeight.bold)),
    const Padding(padding:EdgeInsets.only(top:8,bottom:14),child:Text('Manually refreshed research. No background push alerts in V1.',style:TextStyle(color:secondary,fontSize:12))),
    ...rows.map(_assetTile),if(rows.isEmpty)const Text('Empty. Tap a candidate and add it to your watchlist.')]; }
  List<Widget> _journal()=>[
    const Text('Trade journal',style:TextStyle(fontSize:26,fontWeight:FontWeight.bold)),
    const SizedBox(height:8), const Text('Paper/manual records only. No exchange orders.',style:TextStyle(fontSize:12,color:secondary)),
    const SizedBox(height:12),FilledButton.icon(onPressed:()=>_newTrade(),icon:const Icon(Icons.add),label:const Text('Record trade')),
    ...journal.map((x)=>Card(child:ListTile(title:Text('${x['instrument_id']} · ${x['mode']}'),
      subtitle:Text('Entry ${x['entry']} · Qty ${x['quantity']} · Exit ${x['exit']??'OPEN'}'),
      trailing:Text('${x['realized_pnl']??'—'}',style:const TextStyle(color:mint))))),
    if(journal.isEmpty)const Padding(padding:EdgeInsets.all(24),child:Text('No entries yet.'))];
  Future<void> _newTrade() async {
    if(opportunities.isEmpty)return;
    final saved=await showDialog<bool>(context:context,
      builder:(_)=>_TradeDialog(api:api,opportunities:opportunities,onError:_snack));
    if(saved==true)await refresh();
  }
}

class AssetPage extends StatefulWidget {
  const AssetPage({super.key,required this.api,required this.data,required this.onWatch});
  final SwingApi api;final Map<String,dynamic> data;final Future<void> Function() onWatch;
  @override State<AssetPage> createState()=>_AssetPageState();
}
class _AssetPageState extends State<AssetPage> {
  bool busy=false;
  Future<void> _addWatch() async {
    setState(()=>busy=true);
    try{await widget.api.call('/watchlist',method:'POST',body:{'instrument_id':widget.data['instrument_id']});
      await widget.onWatch();if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Added to watchlist')));
    }catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}finally{if(mounted)setState(()=>busy=false);}
  }
  String _price(dynamic v){if(v==null)return 'UNSUPPORTED';return '${v.toString()} ${widget.data['currency']}';}
  @override Widget build(BuildContext context) {
    final d=widget.data,s=d['setup'] as Map,liq=d['liquidity'] as Map,feature=d['features'] as Map;
    final chart=(d['chart'] as List?)?.map((x)=>(x as Map)['close'] as num).toList() ?? [];
    return Scaffold(appBar:AppBar(title:Text('${d['symbol']}  ·  ${d['market']}')),
      body:ListView(padding:const EdgeInsets.all(16),children:[
        const Text('RESEARCH ONLY · SOURCE AND EXECUTION NOT VERIFIED',style:TextStyle(color:amber,fontSize:11)),
        const SizedBox(height:10),Text(_price(d['last_price']),style:const TextStyle(fontSize:27,fontWeight:FontWeight.bold)),
        Text('${d['data_status']} · ${d['source']} · ${d['as_of']}',style:const TextStyle(color:secondary,fontSize:11)),
        const SizedBox(height:20),Card(child:Padding(padding:const EdgeInsets.all(16),child:Row(children:[
          Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Text(s['strategy'].toString(),style:const TextStyle(fontSize:17,fontWeight:FontWeight.bold)),
            Text('Status: ${s['status']}',style:const TextStyle(color:amber)),
            const Text('Score is NOT a probability',style:TextStyle(color:secondary,fontSize:11))])),
          Text('${s['score']}/100',style:const TextStyle(color:mint,fontSize:24,fontWeight:FontWeight.bold))]))),
        const SizedBox(height:12),SizedBox(height:150,child:CustomPaint(painter:LineChartPainter(chart))),
        const SizedBox(height:12),Row(children:[
          Expanded(child:_mini('ENTRY',_price(s['entry']))),const SizedBox(width:7),
          Expanded(child:_mini('STOP',_price(s['stop']))),const SizedBox(width:7),
          Expanded(child:_mini('STRUCTURAL TARGET',_price(s['target'])))]),
        const SizedBox(height:12),Text('Hypothetical 2R study: ${_price(s['hypothetical_2r_target'])} · not a forecast',style:const TextStyle(color:secondary,fontSize:11)),
        const SizedBox(height:18),const Text('Setup evidence',style:TextStyle(fontSize:18,fontWeight:FontWeight.bold)),
        ...(s['criteria'] as List).map((c)=>ListTile(dense:true,leading:Icon(c['pass']==true?Icons.check_circle_outline:Icons.info_outline,
          color:c['pass']==true?mint:amber),title:Text(c['code'].toString()))),
        const Text('Blocking reasons',style:TextStyle(fontSize:18,fontWeight:FontWeight.bold)),
        ...(s['reason_codes'] as List).map((v)=>Text('• $v',style:const TextStyle(fontSize:12,color:amber))),
        ...((liq['execution_reasons'] as List).map((v)=>Text('• $v',style:const TextStyle(fontSize:12,color:amber)))),
        const SizedBox(height:15),_mini('ADV20 (${liq['adv20_basis']})','${liq['adv20']} ${d['currency']}'),
        const SizedBox(height:8),_mini('EMA20 / EMA50','${feature['ema_20']} / ${feature['ema_50']}'),
        const SizedBox(height:15),const Text('FORECAST NOT VALIDATED',style:TextStyle(fontWeight:FontWeight.bold,color:amber)),
        const Text('Probability and price distribution withheld until walk-forward validation passes.',style:TextStyle(fontSize:11,color:secondary)),
        const SizedBox(height:20),FilledButton.icon(onPressed:busy?null:_addWatch,icon:const Icon(Icons.star_border),label:const Text('Add to watchlist'))
      ]));
  }
  Widget _mini(String label,String value)=>Container(padding:const EdgeInsets.all(10),decoration:BoxDecoration(color:panel,borderRadius:BorderRadius.circular(9)),
    child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(label,style:const TextStyle(fontSize:9,color:secondary)),
      const SizedBox(height:6),Text(value,style:const TextStyle(fontSize:13,fontWeight:FontWeight.bold))]));
}

class LineChartPainter extends CustomPainter {
  LineChartPainter(this.closes);
  final List<num> closes;
  @override void paint(Canvas canvas,Size size) {
    final grid=Paint()..color=const Color(0xFF26384A)..strokeWidth=1;
    for(var i=1;i<=3;i++){final y=size.height*i/4;canvas.drawLine(Offset(0,y),Offset(size.width,y),grid);}
    if(closes.length<2)return;
    final min=closes.map((e)=>e.toDouble()).reduce(math.min),max=closes.map((e)=>e.toDouble()).reduce(math.max);
    final delta=max-min==0?1:max-min;
    final path=Path();
    for(var i=0;i<closes.length;i++){
      final x=(size.width-6)*i/(closes.length-1)+3;
      final y=size.height-5-(size.height-10)*(closes[i]-min)/delta;
      if(i==0){path.moveTo(x,y);}else{path.lineTo(x,y);}
    }
    canvas.drawPath(path,Paint()..color=mint..strokeWidth=2..style=PaintingStyle.stroke);
  }
  @override bool shouldRepaint(covariant LineChartPainter oldDelegate)=>oldDelegate.closes!=closes;
}

class BuilderPage extends StatefulWidget {
  const BuilderPage({super.key,required this.api});
  final SwingApi api;
  @override State<BuilderPage> createState()=>_BuilderPageState();
}
class _BuilderPageState extends State<BuilderPage> {
  final name=TextEditingController(text:'My Swing Scanner');
  String join='AND',strategy='PULLBACK';
  final conditions=<Map<String,dynamic>>[{'field':'close','operator':'GT_FIELD','value':'ema_50'}];
  bool saving=false;
  final fields=['close','ema_20','ema_50','atr_pct','rvol_20','roc_10','adv_20','setup_score'];
  @override void dispose(){name.dispose();super.dispose();}
  Future<void> _save(bool execute) async {
    setState(()=>saving=true);
    try {
      final rules=<String,dynamic>{'op':join,'children':conditions.map((c){
        final type=c['operator'].toString();
        final raw=c['value'].toString();
        dynamic v;
        if(type.endsWith('FIELD')){v=raw;}
        else if(type=='BETWEEN'){v=raw.split(',').map((x)=>double.parse(x.trim())).toList();}
        else{v=double.parse(raw);}
        return {'field':c['field'],'operator':type,'value':v};
      }).toList()};
      final body={'name':name.text,'strategy':strategy,'markets':['US','IDX','CRYPTO'],'rules':rules};
      await widget.api.call('/screeners/validate',method:'POST',body:body);
      await widget.api.call('/screeners',method:'POST',body:body);
      if(execute){await widget.api.call('/screeners/runs',method:'POST',body:body);}
      if(mounted){ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(execute?'Screener saved + executed':'Saved as new version')));Navigator.pop(context);}
    }catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Invalid rule: $e')));}finally{if(mounted)setState(()=>saving=false);}
  }
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Custom Screener')),
    body:ListView(padding:const EdgeInsets.all(16),children:[
      const Text('Rule Builder',style:TextStyle(fontSize:25,fontWeight:FontWeight.bold)),
      const Text('Typed AND/OR conditions. Nested groups available through private API.',style:TextStyle(fontSize:11,color:secondary)),
      TextField(controller:name,decoration:const InputDecoration(labelText:'Screener name')),
      const SizedBox(height:12),DropdownButtonFormField(value:strategy,decoration:const InputDecoration(labelText:'Strategy'),
        items:['PULLBACK','BREAKOUT','BOTH'].map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),onChanged:(x)=>setState(()=>strategy=x??'PULLBACK')),
      const SizedBox(height:12),DropdownButtonFormField(value:join,decoration:const InputDecoration(labelText:'Combine conditions'),
        items:['AND','OR'].map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),onChanged:(x)=>setState(()=>join=x??'AND')),
      const SizedBox(height:12),...List.generate(conditions.length,(i){final c=conditions[i];return Card(child:Padding(padding:const EdgeInsets.all(10),child:Column(children:[
        Row(children:[Expanded(child:DropdownButton<String>(value:c['field'] as String,isExpanded:true,
          items:fields.map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),onChanged:(v)=>setState(()=>c['field']=v))),
          const SizedBox(width:8),IconButton(onPressed:()=>setState(()=>conditions.removeAt(i)),icon:const Icon(Icons.delete_outline))]),
        DropdownButtonFormField<String>(value:c['operator'] as String,items:['GT','GTE','LT','LTE','EQ','BETWEEN','GT_FIELD','LT_FIELD']
          .map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),onChanged:(v)=>setState(()=>c['operator']=v)),
        TextFormField(initialValue:c['value'].toString(),onChanged:(v)=>c['value']=v,decoration:const InputDecoration(labelText:'Value, field, or min,max')),
      ])));
      }),
      OutlinedButton.icon(onPressed:()=>setState(()=>conditions.add({'field':'rvol_20','operator':'GTE','value':'1.5'})),icon:const Icon(Icons.add),label:const Text('Add condition')),
      const SizedBox(height:20),FilledButton(onPressed:saving?null:()=>_save(true),child:const Text('Validate, save version & run')),
      const SizedBox(height:8),OutlinedButton(onPressed:saving?null:()=>_save(false),child:const Text('Save version only'))
    ]));
}

/// Owns its controllers so they are disposed with the dialog's element, after the exit animation.
class _ConnectionDialog extends StatefulWidget {
  const _ConnectionDialog({required this.api, required this.onError});
  final SwingApi api;
  final void Function(String) onError;
  @override State<_ConnectionDialog> createState() => _ConnectionDialogState();
}

class _ConnectionDialogState extends State<_ConnectionDialog> {
  late final url = TextEditingController(text: widget.api.baseUrl);
  late final token = TextEditingController(text: widget.api.token);

  @override void dispose() { url.dispose(); token.dispose(); super.dispose(); }

  Future<void> _connect() async {
    final u = Uri.tryParse(url.text.trim());
    if (u == null || (u.scheme != 'http' && u.scheme != 'https') || u.host.isEmpty) {
      widget.onError('Alamat harus berupa URL http/https valid'); return;
    }
    widget.api.baseUrl = url.text.trim(); widget.api.token = token.text;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', widget.api.baseUrl);
    if (mounted) Navigator.pop(context, true);
  }

  @override Widget build(BuildContext context) => AlertDialog(
    title: const Text('Private backend connection'),
    content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
      const Text('Emulator: http://10.0.2.2:8000. Phone fisik: alamat VPN/private server. Jangan expose API ke internet publik.', style: TextStyle(fontSize: 12)),
      const SizedBox(height: 12),
      TextField(controller: url, decoration: const InputDecoration(labelText: 'API base URL')),
      TextField(controller: token, obscureText: true, decoration: const InputDecoration(labelText: 'Bearer token (opsional di localhost)')),
      const SizedBox(height: 10),
      const Text('Token hanya tersimpan selama aplikasi berjalan; bukan dalam file aplikasi.', style: TextStyle(fontSize: 11, color: secondary))
    ])),
    actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
      FilledButton(onPressed: _connect, child: const Text('Connect'))],
  );
}

class _TradeDialog extends StatefulWidget {
  const _TradeDialog({required this.api, required this.opportunities, required this.onError});
  final SwingApi api;
  final List<Map<String, dynamic>> opportunities;
  final void Function(String) onError;
  @override State<_TradeDialog> createState() => _TradeDialogState();
}

class _TradeDialogState extends State<_TradeDialog> {
  final entry=TextEditingController(),qty=TextEditingController(),exit=TextEditingController();
  late String id=widget.opportunities.first['instrument_id'].toString();

  @override void dispose(){entry.dispose();qty.dispose();exit.dispose();super.dispose();}

  Future<void> _save() async {
    try{
      await widget.api.call('/journal/trades',method:'POST',body:{
        'instrument_id':id,'mode':'PAPER','side':'LONG','entry':entry.text,'quantity':qty.text,
        if(exit.text.isNotEmpty)'exit':exit.text});
      if(mounted)Navigator.pop(context,true);
    }catch(e){widget.onError(e.toString());}
  }

  @override Widget build(BuildContext context) => AlertDialog(
    title:const Text('Record paper trade'),content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
      DropdownButtonFormField<String>(value:id,isExpanded:true,items:{for (final o in widget.opportunities) o['instrument_id'].toString(): o['symbol'].toString()}
        .entries.map((e)=>DropdownMenuItem(value:e.key,child:Text(e.value))).toList(),onChanged:(v)=>setState(()=>id=v??id)),
      TextField(controller:entry,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Entry price')),
      TextField(controller:qty,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Quantity')),
      TextField(controller:exit,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'Exit (optional)'))])),
    actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('Cancel')),
      FilledButton(onPressed:_save,child:const Text('Save'))],
  );
}
