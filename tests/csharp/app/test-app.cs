/**
 * @file test-app.cs
 *
 * encoding: utf-8
 * Copyright (c) 2012 SjB <steve@sagacity.ca>. All Rights Reserved.
 *
 */

using System;

namespace WAF.Test
{
	public static class TestApp {
		public static void Main(string[] args)
		{
			var t = new TestLib();
			Console.WriteLine(t.Name);
		}
	}
}
