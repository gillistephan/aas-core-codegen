/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */

using ArgumentException = System.ArgumentException;
using InvalidOperationException = System.InvalidOperationException;
using NotImplementedException = System.NotImplementedException;
using Regex = System.Text.RegularExpressions.Regex;
using System.Collections.Generic;  // can't alias
using System.Collections.ObjectModel;  // can't alias
using System.Linq;  // can't alias

namespace AasCore.Aas3
{
    public static class Verification
    {
        public static class Pattern
        {
            private static Regex _constructIriRe()
            {
                var scheme = "[a-zA-Z][a-zA-Z0-9+\\-.]*";
                var ucschar = (
                    "[\\xa0-\\ud7ff\\uf900-\\ufdcf\\ufdf0-\\uffef\\u10000-\\u1fffd" +
                    "\\u20000-\\u2fffd\\u30000-\\u3fffd\\u40000-\\u4fffd" +
                    "\\u50000-\\u5fffd\\u60000-\\u6fffd\\u70000-\\u7fffd" +
                    "\\u80000-\\u8fffd\\u90000-\\u9fffd\\ua0000-\\uafffd" +
                    "\\ub0000-\\ubfffd\\uc0000-\\ucfffd\\ud0000-\\udfffd" +
                    "\\ue1000-\\uefffd]"
                );
                var iunreserved = $"([a-zA-Z0-9\\-._~]|{ucschar})";
                var pctEncoded = "%[0-9A-Fa-f][0-9A-Fa-f]";
                var subDelims = $"[!$&'()*+,;=]";
                var iuserinfo = $"({iunreserved}|{pctEncoded}|{subDelims}|:)*";
                var h16 = "[0-9A-Fa-f]{1,4}";
                var dec_octet = "([0-9]|[1-9][0-9]|1[0-9]{2,2}|2[0-4][0-9]|25[0-5])";
                var ipv4address = $"{dec_octet}\\.{dec_octet}\\.{dec_octet}\\.{dec_octet}";
                var ls32 = $"({h16}:{h16}|{ipv4address})";
                var ipv6address = (
                    $"(({h16}:){{6,6}}{ls32}|::({h16}:){{5,5}}{ls32}|({h16})?::({h16}" +
                    $":){{4,4}}{ls32}|(({h16}:)?{h16})?::({h16}:){{3,3}}{ls32}|(({h16}" +
                    $":){{2}}{h16})?::({h16}:){{2,2}}{ls32}|(({h16}:){{3}}{h16})?::{h16}:" +
                    $"{ls32}|(({h16}:){{4}}{h16})?::{ls32}|(({h16}:){{5}}{h16})?::{h16}|" +
                    $"(({h16}:){{6}}{h16})?::)"
                );
                var unreserved = "[a-zA-Z0-9\\-._~]";
                var ipvfuture = $"[vV][0-9A-Fa-f]{{1,}}\\.({unreserved}|{subDelims}|:){{1,}}";
                var ipLiteral = $"\\[({ipv6address}|{ipvfuture})\\]";
                var iregName = $"({iunreserved}|{pctEncoded}|{subDelims})*";
                var ihost = $"({ipLiteral}|{ipv4address}|{iregName})";
                var port = "[0-9]*";
                var iauthority = $"({iuserinfo}@)?{ihost}(:{port})?";
                var ipchar = $"({iunreserved}|{pctEncoded}|{subDelims}|[:@])";
                var isegment = $"({ipchar})*";
                var ipath_abempty = $"(/{isegment})*";
                var isegment_nz = $"({ipchar}){{1,}}";
                var ipath_absolute = $"/({isegment_nz}(/{isegment})*)?";
                var ipathRootless = $"{isegment_nz}(/{isegment})*";
                var ipathEmpty = $"({ipchar}){{0,0}}";
                var ihierPart = (
                    $"(//{iauthority}{ipath_abempty}|{ipath_absolute}|" +
                    $"{ipathRootless}|{ipathEmpty})"
                );
                var iprivate = "[\\ue000-\\uf8ff\\uf0000-\\uffffd\\u100000-\\u10fffd]";
                var iquery = $"({ipchar}|{iprivate}|[/?])*";
                var absoluteIri = $"{scheme}:{ihierPart}(\\?{iquery})?";
                var ifragment = $"({ipchar}|[/?])*";
                var isegmentNzNc = $"({iunreserved}|{pctEncoded}|{subDelims}|@){{1,}}";
                var ipathNoscheme = $"{isegmentNzNc}(/{isegment})*";
                var ipath = (
                    $"({ipath_abempty}|{ipath_absolute}|{ipathNoscheme}|" +
                    $"{ipathRootless}|{ipathEmpty})"
                );
                var irelativePart = (
                    $"(//{iauthority}{ipath_abempty}|{ipath_absolute}|" +
                    $"{ipathNoscheme}|{ipathEmpty})"
                );
                var irelativeRef = $"{irelativePart}(\\?{iquery})?(\\#{ifragment})?";
                var iri = $"{scheme}:{ihierPart}(\\?{iquery})?(\\#{ifragment})?";
                var iriReference = $"({iri}|{irelativeRef})";
    
                return new Regex($"^{iriReference}$");
            }

            private static readonly Regex _IriRegex = _constructIriRe();

            /// <summary>
            /// Check that the <paramref name="text"/> is a valid IRI.
            /// </summary>
            /// <remarks>
            /// Related RFC: https://datatracker.ietf.org/doc/html/rfc3987
            /// </remarks>
            public static bool IsIri(string text)
            {
                return _IriRegex.IsMatch(text);
            }

            private static Regex _constructIrdiRegex()
            {
                var numeric = "[0-9]";
                var safeChar = "[A-Za-z0-9:_.]";

                return new Regex(
                    $"^{numeric}{{4}}-{safeChar}{{1,35}}(-{safeChar}{{1,35}})?" +
                    $"#{safeChar}{{2}}-{safeChar}{{6}}" +
                    $"#{numeric}{{1,35}}$"
                );
            }

            private static readonly Regex _IrdiRegex = _constructIrdiRegex();

            /// <summary>
            /// Check that the <paramref name="text"/> is a valid IRDI.
            /// </summary>
            /// <remarks>
            /// Related ISO standard: https://www.iso.org/standard/50773.html
            /// </remarks>
            public static bool IsIrdi(string text)
            {
                return _IrdiRegex.IsMatch(text);
            }

            private static readonly Regex _idShortRe = new Regex(
                "^[a-zA-Z][a-zA-Z_0-9]*$"
            );

            /// <summary>
            /// Check that the <paramref name="text"/> is a valid short ID.
            /// </summary>
            /// <remarks>
            /// Related: Constraint AASd-002
            /// </remarks>
            public static bool IsIdShort(string text)
            {
                return _idShortRe.IsMatch(text);
            }
        }

        /// <summary>
        /// Represent a verification error traceable to an entity or a property.
        /// </summary>
        public class Error
        {
            /// <summary>
            /// JSON-like path to the related object (an entity or a property)
            /// </summary>
            public readonly string Path;

            /// <summary>
            /// Cause or description of the error
            /// </summary>
            public readonly string Message;

            public Error(string path, string message)
            {
                Path = path;
                Message = message;
            }
        }

        /// <summary>
        /// Contain multiple errors observed during a verification.
        /// </summary>
        public class Errors
        {
            /// <summary>
            /// The maximum capacity of the container
            /// </summary>
            public readonly int Capacity;

            /// <summary>
            /// Contained error items
            /// </summary>
            private readonly List<Error> _entries;

            /// <summary>
            /// Initialize the container with the given <paramref name="capacity" />.
            /// </summary>
            public Errors(int capacity)
            {
                if (capacity <= 0)
                {
                    throw new ArgumentException(
                        $"Expected a strictly positive capacity, but got: {capacity}");
                }

                Capacity = capacity;
                _entries = new List<Error>(Capacity);
            }

            /// <summary>
            /// Add the error to the container if the capacity has not been reached.
            /// </summary>
            public void Add(Error error)
            {
                if(_entries.Count <= Capacity)
                {
                    _entries.Add(error);
                }
            }

            /// <summary>
            /// True if the capacity has been reached.
            /// </summary>
            public bool Full()
            {
                return _entries.Count == Capacity;
            }

            /// <summary>
            /// Retrieve the contained error entries.
            /// </summary>
            /// <remarks>
            /// If you want to add a new error, use <see cref="Add" />.
            /// </remarks>
            public ReadOnlyCollection<Error> Entries()
            {
                var result = this._entries.AsReadOnly();
                if (result.Count > Capacity)
                {
                    throw new InvalidOperationException(
                        $"Post-condition violated: " +
                        $"result.Count (== {result.Count}) > Capacity (== {Capacity})");
                }
                return result;
            }
        }

        /// <summary>
        /// Verify the instances of the model entities non-recursively.
        /// </summary>
        /// <remarks>
        /// The methods provided by this class are re-used in the verification
        /// visitors.
        /// </remarks>
        private static class Implementation
        {
            /// <summary>
            /// Hash allowed enum values for efficient validation of enums.
            /// </summary> 
            private static class EnumValueSet
            {
                public static HashSet<int> ForIdentifierType = new HashSet<int>(
                    System.Enum.GetValues(typeof(IdentifierType)).Cast<int>());

                public static HashSet<int> ForModelingKind = new HashSet<int>(
                    System.Enum.GetValues(typeof(ModelingKind)).Cast<int>());

                public static HashSet<int> ForLocalKeyType = new HashSet<int>(
                    System.Enum.GetValues(typeof(LocalKeyType)).Cast<int>());

                public static HashSet<int> ForKeyType = new HashSet<int>(
                    System.Enum.GetValues(typeof(KeyType)).Cast<int>());

                public static HashSet<int> ForIdentifiableElements = new HashSet<int>(
                    System.Enum.GetValues(typeof(IdentifiableElements)).Cast<int>());

                public static HashSet<int> ForReferableElements = new HashSet<int>(
                    System.Enum.GetValues(typeof(ReferableElements)).Cast<int>());

                public static HashSet<int> ForKeyElements = new HashSet<int>(
                    System.Enum.GetValues(typeof(KeyElements)).Cast<int>());
            }  // private static class EnumValueSet

            /// <summary>
            /// Verify the given <paramref name="langString" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="langString" />.
            /// </summary>
            public static void VerifyLangString (
                LangString langString,
                string path,
                Errors errors)
            {
                // There are no invariants defined for LangString.
            }

            /// <summary>
            /// Verify the given <paramref name="langStringSet" /> and
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="langString" />.
            /// </summary>
            public static void VerifyLangStringSet (
                LangStringSet langStringSet,
                string path,
                Errors errors)
            {
                throw new NotImplementedException("TODO");
            }

            /// <summary>
            /// Verify the given <paramref name="identifier" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="identifier" />.
            /// </summary>
            public static void VerifyIdentifier (
                Identifier identifier,
                string path,
                Errors errors)
            {
                if (errors.Full()) return;

                if (!EnumValueSet.ForIdentifierType.Contains(
                        (int)identifier.IdType))
                {
                    errors.Add(
                        new Error(
                            $"{path}/IdType",
                            $"Invalid {nameof(IdentifierType)}: {identifier.IdType}"));
                }
            }

            /// <summary>
            /// Verify the given <paramref name="administrativeInformation" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="administrativeInformation" />.
            /// </summary>
            public static void VerifyAdministrativeInformation (
                AdministrativeInformation administrativeInformation,
                string path,
                Errors errors)
            {
                // There is no verification specified for AdministrativeInformation.
            }

            /// <summary>
            /// Verify the given <paramref name="key" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="key" />.
            /// </summary>
            public static void VerifyKey (
                Key key,
                string path,
                Errors errors)
            {
                if (errors.Full()) return;

                if (!EnumValueSet.ForKeyElements.Contains(
                        (int)key.Type))
                {
                    errors.Add(
                        new Error(
                            $"{path}/Type",
                            $"Invalid {nameof(KeyElements)}: {key.Type}"));
                }

                if (errors.Full()) return;

                if (!EnumValueSet.ForKeyType.Contains(
                        (int)key.IdType))
                {
                    errors.Add(
                        new Error(
                            $"{path}/IdType",
                            $"Invalid {nameof(KeyType)}: {key.IdType}"));
                }
            }

            /// <summary>
            /// Verify the given <paramref name="reference" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="reference" />.
            /// </summary>
            public static void VerifyReference (
                Reference reference,
                string path,
                Errors errors)
            {
                // There is no verification specified for Reference.
            }

            /// <summary>
            /// Verify the given <paramref name="assetAdministrationShell" /> and 
            /// append any errors to <paramref name="Errors" />.
            ///
            /// The <paramref name="path" /> localizes the <paramref name="assetAdministrationShell" />.
            /// </summary>
            public static void VerifyAssetAdministrationShell (
                AssetAdministrationShell assetAdministrationShell,
                string path,
                Errors errors)
            {
                // There is no verification specified for AssetAdministrationShell.
            }
        }  // private static class Implementation

        /// <summary>
        /// Verify the instances of the model entities non-recursively.
        /// </summary>
        public class NonRecursiveVerifier : 
            Visitation.IVisitorWithContext<string>
        {
            public readonly Errors Errors;

            /// <summary>
            /// Initialize the visitor with the given <paramref name="errors" />.
            ///
            /// The errors observed during the visitation will be appended to
            /// the <paramref name="errors" />.
            /// </summary>
            NonRecursiveVerifier(Errors errors)
            {
                Errors = errors;
            }

            public void Visit(IEntity entity, string context)
            {
                entity.Accept(this, context);
            }

            /// <summary>
            /// Verify <paramref name="langString" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                LangString langString,
                string context)
            {
                Implementation.VerifyLangString(
                    langString,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="langStringSet" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                LangStringSet langStringSet,
                string context)
            {
                Implementation.VerifyLangStringSet(
                    langStringSet,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="identifier" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Identifier identifier,
                string context)
            {
                Implementation.VerifyIdentifier(
                    identifier,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="administrativeInformation" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                AdministrativeInformation administrativeInformation,
                string context)
            {
                Implementation.VerifyAdministrativeInformation(
                    administrativeInformation,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="key" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Key key,
                string context)
            {
                Implementation.VerifyKey(
                    key,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="reference" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Reference reference,
                string context)
            {
                Implementation.VerifyReference(
                    reference,
                    context,
                    Errors);
            }

            /// <summary>
            /// Verify <paramref name="assetAdministrationShell" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                AssetAdministrationShell assetAdministrationShell,
                string context)
            {
                Implementation.VerifyAssetAdministrationShell(
                    assetAdministrationShell,
                    context,
                    Errors);
            }
        }  // public class NonRecursiveVerifier

        /// <summary>
        /// Verify the instances of the model entities recursively.
        /// </summary>
        public class RecursiveVerifier : 
            Visitation.IVisitorWithContext<string>
        {
            public readonly Errors Errors;

            /// <summary>
            /// Initialize the visitor with the given <paramref name="errors" />.
            ///
            /// The errors observed during the visitation will be appended to
            /// the <paramref name="errors" />.
            /// </summary>
            RecursiveVerifier(Errors errors)
            {
                Errors = errors;
            }

            public void Visit(IEntity entity, string context)
            {
                entity.Accept(this, context);
            }

            /// <summary>
            /// Verify recursively <paramref name="langString" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                LangString langString,
                string context)
            {
                Implementation.VerifyLangString(
                    langString,
                    context,
                    Errors);

                // The recursion ends here.
            }

            /// <summary>
            /// Verify recursively <paramref name="langStringSet" /> and
            /// append any error to <see cref="Errors" />
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                LangStringSet langStringSet,
                string context)
            {
                throw new NotImplementedException("TODO");
            }

            /// <summary>
            /// Verify recursively <paramref name="identifier" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Identifier identifier,
                string context)
            {
                Implementation.VerifyIdentifier(
                    identifier,
                    context,
                    Errors);

                // The recursion ends here.
            }

            /// <summary>
            /// Verify recursively <paramref name="administrativeInformation" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                AdministrativeInformation administrativeInformation,
                string context)
            {
                Implementation.VerifyAdministrativeInformation(
                    administrativeInformation,
                    context,
                    Errors);

                // The recursion ends here.
            }

            /// <summary>
            /// Verify recursively <paramref name="key" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Key key,
                string context)
            {
                Implementation.VerifyKey(
                    key,
                    context,
                    Errors);

                // The recursion ends here.
            }

            /// <summary>
            /// Verify recursively <paramref name="reference" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                Reference reference,
                string context)
            {
                Implementation.VerifyReference(
                    reference,
                    context,
                    Errors);

                if (Errors.Full()) return;

                for(var i = 0; i < reference.Keys.Count; i++)
                {
                    Visit(
                        reference.Keys[i],
                        $"{context}/Keys/{i}");
                }
            }

            /// <summary>
            /// Verify recursively <paramref name="assetAdministrationShell" /> and
            /// append any error to <see cref="Errors" /> 
            /// where <paramref name="context" /> is used to localize the error.
            /// </summary>
            public void Visit(
                AssetAdministrationShell assetAdministrationShell,
                string context)
            {
                Implementation.VerifyAssetAdministrationShell(
                    assetAdministrationShell,
                    context,
                    Errors);

                if (Errors.Full()) return;

                if (assetAdministrationShell.DisplayName != null)
                {
                    Visit(
                        assetAdministrationShell.DisplayName,
                        $"{context}/DisplayName");
                }

                if (Errors.Full()) return;

                if (assetAdministrationShell.Description != null)
                {
                    Visit(
                        assetAdministrationShell.Description,
                        $"{context}/Description");
                }

                if (Errors.Full()) return;

                Visit(
                    assetAdministrationShell.Identification,
                    $"{context}/Identification");

                if (Errors.Full()) return;

                if (assetAdministrationShell.Administration != null)
                {
                    Visit(
                        assetAdministrationShell.Administration,
                        $"{context}/Administration");
                }

                if (Errors.Full()) return;

                for(
                    var i = 0;
                    i < assetAdministrationShell.DataSpecifications.Count;
                    i++)
                {
                    Visit(
                        assetAdministrationShell.DataSpecifications[i],
                        $"{context}/DataSpecifications/{i}");
                }

                if (Errors.Full()) return;

                if (assetAdministrationShell.DerivedFrom != null)
                {
                    Visit(
                        assetAdministrationShell.DerivedFrom,
                        $"{context}/DerivedFrom");
                }
            }
        }  // public class RecursiveVerifier
    }  // public static class Verification
}  // namespace AasCore.Aas3

/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */
