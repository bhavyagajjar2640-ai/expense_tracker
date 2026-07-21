import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';

import 'auth_page.dart';

class DashboardPage extends StatefulWidget {
  final int userId;
  final String username;

  const DashboardPage({
    super.key,
    required this.userId,
    required this.username,
  });

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  bool _isLoading = true;
  bool _hasData = false;
  String _errorMessage = '';

  // Dashboard Metrics
  double _total = 0.0;
  double _average = 0.0;
  String _topCategory = '';
  Map<String, dynamic> _categoryTotals = {};

  // Expense List
  List<dynamic> _expenses = [];

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final dashboardRes = await http.get(Uri.parse('http://10.0.2.2:8000/api/dashboard/${widget.userId}'));
      final expensesRes = await http.get(Uri.parse('http://10.0.2.2:8000/api/expenses/${widget.userId}'));

      if (dashboardRes.statusCode == 200 && expensesRes.statusCode == 200) {
        final dashData = jsonDecode(dashboardRes.body);
        final expData = jsonDecode(expensesRes.body);

        if (dashData['has_data'] == true) {
          setState(() {
            _hasData = true;
            _total = dashData['metrics']['total'];
            _average = dashData['metrics']['average'];
            _topCategory = dashData['metrics']['top_category'];
            _categoryTotals = dashData['category_totals'];
            _expenses = expData['expenses'] ?? [];
            _isLoading = false;
          });
        } else {
          setState(() {
            _hasData = false;
            _isLoading = false;
            _errorMessage = dashData['message'] ?? 'No data found.';
          });
        }
      } else {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Failed to load data. Status code error.';
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Error connecting to the server: $e';
      });
    }
  }

  void _logout() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const AuthPage()),
    );
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _deleteExpense(int id) async {
    try {
      final response = await http.delete(Uri.parse('http://10.0.2.2:8000/api/expenses/${widget.userId}/$id'));
      if (response.statusCode == 200) {
        _fetchData(); // refresh
      } else {
        _showError('Failed to delete expense');
      }
    } catch (e) {
      _showError('Error: $e');
    }
  }

  void _showExpenseDialog({Map<String, dynamic>? expense}) {
    final isEdit = expense != null;
    final dateController = TextEditingController(text: isEdit ? expense['date'] : DateTime.now().toString().split(' ')[0]);
    final categoryController = TextEditingController(text: isEdit ? expense['category'] : '');
    final amountController = TextEditingController(text: isEdit ? expense['amount'].toString() : '');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'Edit Expense' : 'Add Expense'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: dateController, decoration: const InputDecoration(labelText: 'Date (YYYY-MM-DD)')),
            SizedBox(height: 5),
            TextField(controller: categoryController, decoration: const InputDecoration(labelText: 'Category')),
            SizedBox(height: 5),
            TextField(controller: amountController, decoration: const InputDecoration(labelText: 'Amount'), keyboardType: TextInputType.number),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final body = jsonEncode({
                'date': dateController.text,
                'category': categoryController.text,
                'amount': double.tryParse(amountController.text) ?? 0.0,
              });
              Navigator.pop(ctx);

              try {
                http.Response res;
                if (isEdit) {
                  final expId = expense['id'];
                  if (expId == null) {
                    _showError('Cannot edit this expense. Please refresh the page first.');
                    return;
                  }
                  res = await http.put(
                    Uri.parse('http://10.0.2.2:8000/api/expenses/${widget.userId}/$expId'),
                    headers: {'Content-Type': 'application/json'},
                    body: body,
                  );
                } else {
                  res = await http.post(
                    Uri.parse('http://10.0.2.2:8000/api/expenses/${widget.userId}'),
                    headers: {'Content-Type': 'application/json'},
                    body: body,
                  );
                }
                if (res.statusCode == 200) {
                  _fetchData();
                } else {
                  _showError('Failed to save expense');
                }
              } catch (e) {
                _showError('Error: $e');
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCards() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 600;
        return Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _MetricCard(
              title: 'Total Expenses',
              value: '₹${_total.toStringAsFixed(2)}',
              icon: Icons.account_balance_wallet_rounded,
              color: const Color(0xFF0F766E),
              width: isWide ? (constraints.maxWidth / 3) - 16 : constraints.maxWidth,
            ),
            _MetricCard(
              title: 'Average',
              value: '₹${_average.toStringAsFixed(2)}',
              icon: Icons.analytics_rounded,
              color: const Color(0xFFF59E0B),
              width: isWide ? (constraints.maxWidth / 3) - 16 : constraints.maxWidth,
            ),
            _MetricCard(
              title: 'Top Category',
              value: _topCategory,
              icon: Icons.category_rounded,
              color: const Color(0xFF3B82F6),
              width: isWide ? (constraints.maxWidth / 3) - 16 : constraints.maxWidth,
            ),
          ],
        );
      },
    );
  }

  Widget _buildPieChart() {
    if (_categoryTotals.isEmpty) return const SizedBox.shrink();

    final colors = [
      const Color(0xFF0F766E),
      const Color(0xFFF59E0B),
      const Color(0xFF3B82F6),
      const Color(0xFF8B5CF6),
      const Color(0xFFEC4899),
      const Color(0xFF10B981),
    ];

    int i = 0;
    final sections = _categoryTotals.entries.map((entry) {
      final color = colors[i % colors.length];
      i++;
      return PieChartSectionData(
        color: color,
        value: (entry.value as num).toDouble(),
        title: entry.key,
        radius: 60,
        titleStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          shadows: [Shadow(color: Colors.black26, blurRadius: 2)],
        ),
      );
    }).toList();

    return Container(
      height: 300,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Expenses by Category',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 24),
          Expanded(
            child: PieChart(
              PieChartData(
                sections: sections,
                centerSpaceRadius: 40,
                sectionsSpace: 2,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpenseList() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Recent Transactions',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 16),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _expenses.length > 10 ? 10 : _expenses.length,
            separatorBuilder: (context, index) => const Divider(height: 32),
            itemBuilder: (context, index) {
              final exp = _expenses[index];
              return InkWell(
                onTap: () => _showExpenseDialog(expense: exp),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F766E).withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.receipt_long_rounded,
                          color: Color(0xFF0F766E),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              exp['category'] ?? 'Unknown',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              exp['date'] ?? '',
                              style: TextStyle(
                                color: Colors.grey.shade600,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        '₹${(exp['amount'] as num).toStringAsFixed(2)}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, color: Colors.red),
                        onPressed: () {
                          final id = exp['id'];
                          if (id != null) {
                            _deleteExpense(id as int);
                          } else {
                            _showError('Cannot delete this expense. Please refresh the page first.');
                          }
                        },
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7FA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: Text(
          'Dashboard',
          style: const TextStyle(
            color: Color(0xFF0F172A),
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          Center(
            child: Padding(
              padding: const EdgeInsets.only(right: 16.0),
              child: Text(
                'Hi, ${widget.username}',
                style: const TextStyle(
                  color: Color(0xFF0F766E),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Color(0xFF0F172A)),
            onPressed: _logout,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showExpenseDialog(),
        backgroundColor: const Color(0xFF0F766E),
        child: const Icon(Icons.add, color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _errorMessage,
                        style: const TextStyle(color: Colors.red, fontSize: 16),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _fetchData,
                        child: const Text('Retry'),
                      )
                    ],
                  ),
                )
              : !_hasData
                  ? const Center(
                      child: Text(
                        'No document uploaded yet. Please use the web portal to upload data.',
                        style: TextStyle(fontSize: 16),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _fetchData,
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildSummaryCards(),
                            const SizedBox(height: 24),
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final isWide = constraints.maxWidth > 800;
                                if (isWide) {
                                  return Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                        flex: 1,
                                        child: _buildPieChart(),
                                      ),
                                      const SizedBox(width: 24),
                                      Expanded(
                                        flex: 2,
                                        child: _buildExpenseList(),
                                      ),
                                    ],
                                  );
                                } else {
                                  return Column(
                                    children: [
                                      _buildPieChart(),
                                      const SizedBox(height: 24),
                                      _buildExpenseList(),
                                    ],
                                  );
                                }
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final double width;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    required this.width,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color, size: 32),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  value,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
