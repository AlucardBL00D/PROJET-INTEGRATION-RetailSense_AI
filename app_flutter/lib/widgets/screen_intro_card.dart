import 'package:flutter/material.dart';

class ScreenIntroCard extends StatelessWidget {
  final String title;
  final String description;
  final List<String> bullets;

  const ScreenIntroCard({
    super.key,
    required this.title,
    required this.description,
    required this.bullets,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFFEFF7F6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
                color: const Color(0xFF0B5F5A),
              ),
            ),
            const SizedBox(height: 6),
            Text(description),
            if (bullets.isNotEmpty) ...[
              const SizedBox(height: 10),
              ...bullets.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(
                          Icons.check_circle_outline,
                          size: 16,
                          color: Color(0xFF0B5F5A),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(child: Text(item)),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
